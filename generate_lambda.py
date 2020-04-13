import os
import zipfile

file_name = "app.zip"

zf = zipfile.ZipFile(file_name, "w", zipfile.ZIP_DEFLATED, compresslevel=9)

zf.write("app.py")

os.chdir("Lib\site-packages")
for dirname, subdirs, files in os.walk("./"):
    if "./pip" not in dirname:
        zf.write(dirname)
        for filename in files:
            zf.write(os.path.join(dirname, filename))