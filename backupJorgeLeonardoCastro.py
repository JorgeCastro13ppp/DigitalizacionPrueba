#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import logging
import zipfile
import argparse

# ========================
# CONFIGURACIÓN
# ========================
# Carpeta base donde están tus proyectos
PROYECTOS_BASE = Path("/home/diurno/Escritorio/DASP")

# Carpeta destino NAS / red
DESTINO_NAS = Path("/mnt/nas/backup_proyectos")  # Cambia según tu red

# Log de actividad
LOG_FILE = str(Path(__file__).parent / "backup.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ========================
# FUNCIONES AUXILIARES
# ========================
def encontrar_repos_git(base_path):
    """Devuelve lista de subdirectorios que son repositorios Git"""
    repositorios = []
    for sub in base_path.iterdir():
        if sub.is_dir() and (sub / ".git").exists():
            repositorios.append(sub)
    return repositorios

def zip_folder(folder_path, zip_path):
    """Comprime toda la carpeta en un archivo zip"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = Path(root) / file
                zipf.write(full_path, full_path.relative_to(folder_path))
    logging.info(f"Carpeta comprimida en {zip_path}")

def backup_to_nas():
    """Copia incremental hacia NAS con compresión"""
    if not DESTINO_NAS.exists():
        DESTINO_NAS.mkdir(parents=True)
        logging.info(f"Se creó la carpeta destino: {DESTINO_NAS}")

    resumen = []
    for proyecto in PROYECTOS_BASE.iterdir():
        if proyecto.is_dir():
            zip_name = f"{proyecto.name}_{datetime.now().strftime('%Y%m%d')}.zip"
            zip_path = DESTINO_NAS / zip_name

            # Evita duplicados: solo si no existe
            if zip_path.exists():
                logging.info(f"{zip_name} ya existe, se omite")
                continue

            zip_folder(proyecto, zip_path)
            resumen.append(zip_name)
    return resumen

def backup_to_github(repositorios):
    """Hace git push automático de repositorios locales"""
    actualizado = []
    for repo in repositorios:
        try:
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            # Evita error si no hay cambios
            result = subprocess.run(
                ["git", "-C", str(repo), "commit", "-m", "Backup automático"],
                check=False, capture_output=True, text=True
            )
            if "nothing to commit" in result.stdout.lower():
                logging.info(f"No hay cambios en {repo.name}, se omite commit")
            else:
                logging.info(f"Commit realizado en {repo.name}")
                subprocess.run(["git", "-C", str(repo), "push"], check=True)
                logging.info(f"Backup GitHub realizado para {repo.name}")
                actualizado.append(repo.name)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error en repo {repo.name}: {e}")
    return actualizado

# ========================
# SCRIPT PRINCIPAL
# ========================
def main():
    parser = argparse.ArgumentParser(description="Backup automático proyectos DAM")
    parser.add_argument('--nas', action='store_true', help='Hacer copia hacia NAS')
    parser.add_argument('--github', action='store_true', help='Hacer backup hacia GitHub')
    args = parser.parse_args()

    logging.info("===== INICIO DE COPIA DE SEGURIDAD =====")
    print("Inicio de backup...")

    resumen_nas = []
    resumen_github = []

    if args.nas:
        resumen_nas = backup_to_nas()
        print(f"Archivos copiados a NAS: {resumen_nas}")

    if args.github:
        repositorios_git = encontrar_repos_git(PROYECTOS_BASE)
        if not repositorios_git:
            print("No se encontraron repositorios Git en la carpeta base.")
            logging.warning("No se encontraron repositorios Git en la carpeta base")
        else:
            resumen_github = backup_to_github(repositorios_git)
            print(f"Repositorios actualizados en GitHub: {resumen_github}")

    if not args.nas and not args.github:
        print("No se especificó ningún destino. Usa --nas y/o --github")
        logging.warning("No se especificó destino de backup")

    logging.info("===== FIN DE COPIA DE SEGURIDAD =====")
    logging.info(f"Resumen NAS: {resumen_nas}")
    logging.info(f"Resumen GitHub: {resumen_github}")

if __name__ == "__main__":
    main()
