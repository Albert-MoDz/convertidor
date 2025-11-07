# Guía de Uso de Entornos Virtuales en Python

Este documento describe cómo crear y manejar entornos virtuales en Python tanto en **Linux** como en **Windows**, así como instalar dependencias necesarias para tu proyecto.

---

## 🐧 Linux

### 1. Instalación de Python y pip (si no están instalados)

#### Debian/Ubuntu:
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
Arch Linux:
bash
Copiar código
sudo pacman -S python python-pip
Fedora:
bash
Copiar código
sudo dnf install python3 python3-pip
2. Crear un entorno virtual
bash
Copiar código
python3 -m venv venv
Esto crea un entorno virtual llamado venv dentro del proyecto.

3. Activar el entorno virtual
bash
Copiar código
source venv/bin/activate
Deberías ver que tu terminal ahora indica que estás dentro del entorno virtual.

4. Instalar dependencias dentro del entorno
bash
Copiar código
pip install flask yt-dlp
