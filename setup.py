from setuptools import setup

APP = ['main.py']  # Replace 'main.py' with the path to your main script if different
DATA_FILES = ['i18n_id.qm', 'i18n_it.qm', 'i18n_en.qm']
OPTIONS = {
    'argv_emulation': False,
    'excludes': ['Carbon'],
    'iconfile': 'icon.icns',
    'packages': ['cv2', 'PyQt5','carbon']
      # Exclude unnecessary packages
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
