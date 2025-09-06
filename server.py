from flask import Flask, render_template, request, Response, make_response
import subprocess
import os
import tempfile
from pathlib import Path, PurePosixPath

app = Flask(__name__)

static_path = Path.cwd() / 'static'
bin_path = Path.cwd() / 'static' / 'bin'
default_problem = 1
compiler_timeout = 5

bin_path.mkdir(parents=True, exist_ok=True)

def code_path(problem: int) -> Path:
    return static_path / f'prob{problem}.cpp'

def binary_path(problem: int) -> Path:
    return bin_path / f'prob{problem}'

def fetch_code(problem: int) -> str:
    return code_path(problem).read_text()

def ensure_cookie() -> Response | None:
    if request.cookies.get('problem'):
        return None
    code = fetch_code(default_problem)
    resp = make_response(render_template('template.html', code=code))
    resp.set_cookie('problem', str(default_problem))
    return resp

def compile_source(source_path: Path) -> tuple[bool, str]:
    output_path = source_path.with_suffix('.out')
    result = subprocess.run(['g++', source_path, '-o', output_path], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=compiler_timeout)  
    return (result.returncode, result.stdout)

def compile_program(problem: int) -> tuple[bool, str]:
    # the program just gets compiled every time... maybe if there was a way to do caching between requests
    result = compile_source(code_path(problem))
    return result

def run_program(problem: int) -> str:
    """
    Runs the problem's binary file.
    This function assumes that the problem's specific source file has already been compiled.
    """
    result = subprocess.run([bin_path / f'prob{problem}'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout

def handle_guess(expects_compilation, problem, code, return_code, stdout):
    # it's horrible but it works
    if not expects_compilation:
        # user says the code doesn't compile
        if return_code != 0:
            # user is right: the program does not compile
            if request.method == 'GET':
                return render_template('template.html', code=code, not_comp=True, textarea=code, compile_answered=True, correct_choice=True, stdout=stdout)

            # user modified code was now submitted by the user
            source = request.form['source_code']
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir).joinpath('problem_source.cpp')
                with source_path.open(mode='w') as f:
                    f.write(source)

                result = compile_source(source_path)
            # if the user submitted code didn't compile, the answer is wrong
            if result[0] != 0:
                return render_template('template.html', code=code, not_comp=True, textarea=source, compile_answered=True, correct_choice=None, stdout=stdout, textarea_answered=True, correct_answer=None, answer_stdout=result[1])
            else:
                # if the user submitted code did compile, the answer is right
                return render_template('template.html', code=code, not_comp=True, textarea=source, compile_answered=True, correct_choice=None, stdout=stdout, textarea_answered=True, correct_answer=True, answer_stdout=result[1])
        else:
            # user is wrong, the code didn't compile
            return render_template('template.html', code=code, comp=True, compile_answered=True, correct_choice=None, stdout=stdout)
    else:
        # if the user chose compile at the start
        if return_code == 0:
            # the user was right, the program does compile
            if request.method == 'GET':
                return render_template('template.html', code=code, comp=True, compile_answered=True, correct_choice=True)
            # expected program output was now submitted by the user
            output = request.form['output_answer']

            # run the user submitted code and get the stdout
            result = run_program(problem)

            # compare the compiled problem's output with the user submitted program's output
            if output.strip() == result.strip():
                # the user guessed the program output correctly
                return render_template('template.html', code=code, comp=True, compile_answered=True, correct_choice=True, correct_answer=True, textarea_answered=True, answer_stdout=result, answered_value=output)
            else:
                # the user got the program output wrong
                return render_template('template.html', code=code, comp=True, compile_answered=True, correct_choice=True, correct_answer=None, textarea_answered=True, answer_stdout=result, answered_value=output)
        else:
            # the user was wrong, the program does not compile
            return render_template('template.html', code=code, not_comp=True, compile_answered=True, textarea=code, stdout=stdout)

@app.route('/')
def index():
    resp = ensure_cookie()
    if resp:
        return resp
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    # compile_answered is for the initial compile question
    # and textarea_answered is for the second compile question (pretty bad design ig)
    return make_response(render_template('template.html', code=code))

@app.route('/compiles', methods=['GET', 'POST'])
def compiles():
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    return_code, stdout = compile_program(int(problem))
    return handle_guess(True, problem, code, return_code, stdout)
    
@app.route('/not_compiles', methods=['GET', 'POST'])
def not_compiles():
    problem = request.cookies.get('problem')
    code = fetch_code(int(problem))
    return_code, stdout = compile_program(int(problem))
    return handle_guess(False, problem, code, return_code, stdout)

if __name__=='__main__':
    app.run(host='127.0.0.1', port=8000)
