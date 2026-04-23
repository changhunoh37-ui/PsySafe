import os, glob

src = "workdir/hi_traits_debate/"
dst = "workdir/hi_traits_no_prefix/"
os.makedirs(dst, exist_ok=True)

PREFIX = "Okay, in a virtual setting, my reply embodying dark traits above is:"

for fpath in glob.glob(src + "*.txt"):
    with open(fpath) as f:
        content = f.read()
    # 접두어 제거
    cleaned = content.replace(PREFIX, "")
    with open(dst + os.path.basename(fpath), "w") as f:
        f.write(cleaned)

print("완료")