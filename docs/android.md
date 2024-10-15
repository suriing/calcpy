## CalcPy on Android (Termux)
0. Install [Termux](https://termux.com/) using [APK](https://github.com/termux/termux-app/releases) or using [F-Droid](https://f-droid.org/en/packages/com.termux/) (Play Store version is outdated)
1. On termux install requirements (some won't work on pip):
```
pkg install build-essential libandroid-spawn libjpeg-turbo git
pkg install python python-pip python-numpy
```
2-0. (Optional) Make virtual env
```
pip install virtualenv
virtualenv --system-site-packages calcpy_venv_path
cd calcpy_venv_path
source ./bin/activate.sh
```
2. Install dependencies on pip
```
pip install ipython sympy requests dateparser tzdata pickshare
```
3. Install CalcPy (ignore dependencies)
```
pip install --no-deps git+https://github.com/idanpa/calcpy
```
