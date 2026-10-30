"""Inicializador local sem corretora, segredos ou execução financeira."""
import datetime
from pathlib import Path
import subprocess
import sys
import venv
import webbrowser

def main():
    if sys.version_info < (3,12):
        raise SystemExit("Instale Python 3.12 ou superior para executar o projeto.")
    root=Path(__file__).resolve().parent
    env=root/'.venv'
    exe=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    if not exe.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    subprocess.run([str(exe),'-m','pip','install','-e','.[test]'],cwd=root,check=True)
    subprocess.run([str(exe),'-m','pytest','-q'],cwd=root,check=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out=root/'data'/('demo-'+stamp)
    subprocess.run([str(exe),'-m','nazaret_quant.cli','demo','--output',str(out)],cwd=root,check=True)
    report=out/'reports'/'momentum'/'report.html'
    print('Teste funcional concluído. Dados sintéticos; ordens reais indisponíveis.')
    print(report)
    webbrowser.open(report.as_uri())

if __name__=='__main__':
    main()
