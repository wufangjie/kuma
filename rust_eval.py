"""
This script evaluates a Rust code string, and then prints out the expression on the last line of the string. 
It does so by creating a temporary Rust project and insert the given code into the main function in main.rs.
"""
import os
TEMP_DIR = os.path.expanduser('~') 
TEMP_PROJECT_NAME = 'temp_eval_rust'

CODE_TEMPLATE = """

// https://stackoverflow.com/questions/21747136/how-do-i-print-the-type-of-a-variable-in-rust
// NOTE: must be used for a debug purpose only:
pub fn type_of<T>(_: &T) -> &str {
    std::any::type_name::<T>()
}

// `#[macro_export]` will be exported at the root of the crate
// NOTE: dbg!(var1, var2) is ok, but dbgt! cannot
#[macro_export]
macro_rules! dbgt {
    ($val:expr) => {
        match $val {
            tmp => {
                eprintln!(
                    "[{}:{}] ({}: {}) = {:#?}",
                    file!(),
                    line!(),
                    stringify!($val),
                    $crate::type_of(tmp), // not $val, &tmp
                    &tmp
                );
                tmp
            }
        }
    };
}


fn main() {
{CODE_PLACEHOLDER}
}
"""

def decorate_rust_code(rust_code_str):
    rust_code_str = rust_code_str.replace('\\n', '\n')
    lines = rust_code_str.splitlines()
    last_line = lines[-1]
    last_line = last_line.strip()
    last_line.rstrip(';')
    last_line = 'let var_to_eval = ' + last_line + ';'
    lines[-1] = last_line
    lines.append('dbgt!(&var_to_eval);')
    return '\n'.join(lines)

def rust_eval(rust_code_str, temp_dir=TEMP_DIR):
    os.chdir(temp_dir)
    
    # avoid accidentaly deleting important directories
    assert ' ' not in TEMP_PROJECT_NAME and 'temp' in TEMP_PROJECT_NAME
    
    os.system("rm -rf " + TEMP_PROJECT_NAME)
    os.system("cargo new " + TEMP_PROJECT_NAME)
    rust_code_str = decorate_rust_code(rust_code_str)
    rust_code_str = CODE_TEMPLATE.replace("{CODE_PLACEHOLDER}", rust_code_str)
    with open(os.path.join(TEMP_PROJECT_NAME, 'src/main.rs'), 'w', encoding='utf-8') as f:
        f.write(rust_code_str)

    os.chdir(TEMP_PROJECT_NAME)
    os.system('cargo run')

if __name__ == '__main__':
    import sys
    code = '"345".parse::<f64>()'
    if len(sys.argv) > 1:
        code = sys.argv[1]
    rust_eval(code)

