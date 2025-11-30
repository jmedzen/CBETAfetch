README - Sutra process

A. Manually, parse cbeta online reader urls and dl into txt/zip files
 curl -O http://cbdata.dila.edu.tw/v1.2/download/text/C[1163-1937].txt.zip
 curl -O https://cbdata.dila.edu.tw/stable/download/text/T[0353-0499].txt.zip

 use xargs to download multiple urls in a file.
 xargs -n 1 curl -O < urls-in-file.txt

B. script will unzip + combine all the text file under the specific folder.

Terminal Cmds:
 python process.py [path_to_extracted_folders]

Example:

 project_folder是主目錄, 裡面有T1571這個目錄, 可以放很多個也行。
 ~/Download/project/
 #python process.py ~/Downloads/project/

 #python process.py -h
 #python process.py --project working_dir -->原本的行為
 #python process.py --project working_dir --remove  -->就會刪除檔案


DEMO:
$ python process.py project_folder
Working folder:project_folder
processing folder project_folder/T1571
SUTRA_NAME: 大乘廣百論釋論
SUTRA_ID: T1571
SUTRA_VOLS: 10
Saving to project_folder/10_《大乘廣百論釋論》.txt
processing txt: project_folder/T1571/T1571_001.txt
processing txt: project_folder/T1571/T1571_002.txt
processing txt: project_folder/T1571/T1571_003.txt
processing txt: project_folder/T1571/T1571_004.txt
processing txt: project_folder/T1571/T1571_005.txt
processing txt: project_folder/T1571/T1571_006.txt
processing txt: project_folder/T1571/T1571_007.txt
processing txt: project_folder/T1571/T1571_008.txt
processing txt: project_folder/T1571/T1571_009.txt
processing txt: project_folder/T1571/T1571_010.txt
Finished processing project_folder/10_《大乘廣百論釋論》.txt
