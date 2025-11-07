# convertidor
convertidor de youtube en flask


🐧 Linux (Debian/Ubuntu, Arch, Fedora, etc.)
1. Instalar Python y pip (si no los tienes)
Debian/Ubuntu:
sudo apt update && sudo apt install python3 python3-pip python3-venv

Arch Linux:
sudo pacman -S python python-pip

Fedora:
sudo dnf install python3 python3-pip

2. Crear un entorno virtual
python3 -m venv venv


Esto creará una carpeta llamada venv en tu proyecto donde estará el entorno virtual.

3. Activar el entorno virtual
source venv/bin/activate


Verás que el prompt cambia, ahora estás “dentro” del entorno.

4. Instalar tus dependencias en el entorno

Ejemplo con Flask y yt-dlp:

pip install flask yt-dlp


Pro tip: usa pip freeze > requirements.txt para guardar dependencias.
