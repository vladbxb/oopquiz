from flask import Flask, render_template, request, Response, make_response
import subprocess
import os
import tempfile

app = Flask(__name__)

cwd = os.getcwd()

default_problem = 2
compiler_timeout = 5

def fetch_code(problem: int) -> str:
    code = None
    with open(f'static/prob{problem}.cpp', 'r') as f:
        code = f.read()
    return code

def ensure_cookie() -> Response | None:
    problem = request.cookies.get('problem')
    if problem:
        return None
    code = fetch_code(default_problem)
    resp = make_response(render_template('template.html', code=code, not_answered="true"))
    resp.set_cookie('problem', f'{default_problem}')
    return resp

def compile(problem: int) -> (bool, str):
    if not os.path.exists(f'{cwd}/static/bin'):
        os.mkdir(f'{cwd}/static/bin')
    result = subprocess.run(['g++', f'{cwd}/static/prob{problem}.cpp', '-o', f'{cwd}/static/bin/prob{problem}'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=compiler_timeout)  
    return (result.returncode, result.stdout)

def run(problem: int) -> str:
    if not os.path.exists(f'{cwd}/static/bin'):
        os.mkdir(f'{cwd}/static/bin')
    subprocess.run(['g++', f'{cwd}/static/prob{problem}.cpp', '-o', f'{cwd}/static/bin/prob{problem}'], text=True)  
    result = subprocess.run([f'{cwd}/static/bin/prob{problem}'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout


def handle_compile(compiles, problem, code, return_code, stdout):
    if not compiles:
        if return_code != 0:
            if request.method == 'GET':
                return render_template('template.html', code=code, not_comp="true", textarea=code, not_answered=None, correct_choice="true", stdout=stdout)
            
            source = request.form['source_code']
            result = None
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = os.path.join(tmpdir, 'problem_source.cpp')
                output_path = os.path.join(tmpdir, 'problem_source.out')

                with open(source_path, 'w') as f:
                    f.write(source)

                result = subprocess.run(['g++', source_path, '-o', output_path], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=compiler_timeout)
            if result.returncode != 0:
                return render_template('template.html', code=code, not_comp="true", textarea=source, not_answered=None, correct_choice=None, stdout=stdout, answered="true", correct_answer=None, answer_stdout=result.stdout)
            else:
                return render_template('template.html', code=code, not_comp="true", textarea=source, not_answered=None, correct_choice=None, stdout=stdout, answered="true", correct_answer="true", answer_stdout=result.stdout)
        else:
            return render_template('template.html', code=code, comp="true", not_answered=None, correct_choice=None, stdout=stdout)
    else:
        # if the user chose compile at the start
        if return_code == 0:
            if request.method == 'GET':
                return render_template('template.html', code=code, comp="true", correct_choice="true")
            output = request.form['output_answer']

            result = run(problem)

            if output.strip() == result.strip():
                return render_template('template.html', code=code, comp="true", correct_choice="true", correct_answer="true", answered="true", answer_stdout=result, answered_value=output)
            else:
                return render_template('template.html', code=code, comp="true", correct_choice="true", correct_answer=None, answered="true", answer_stdout=result, answered_value=output)
        else:
            return render_template('template.html', code=code, not_comp="true", textarea=code, stdout=stdout)

@app.route('/')
def index():
    resp = ensure_cookie()
    if resp:
        return resp
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    # not_answered is for the initial compile question
    # 
    #
    #
    # and answered is for the second compile question (pretty bad design ig)
    return make_response(render_template('template.html', code=code, not_answered="true"))

@app.route('/compiles', methods=['GET', 'POST'])
def compiles():
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    return_code, stdout = compile(int(problem))
    return handle_compile(True, problem, code, return_code, stdout)
    
@app.route('/not_compiles', methods=['GET', 'POST'])
def not_compiles():
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    return_code, stdout = compile(int(problem))
    return handle_compile(False, problem, code, return_code, stdout)

if __name__=='__main__':
    app.run(host='127.0.0.1', port=8000)
