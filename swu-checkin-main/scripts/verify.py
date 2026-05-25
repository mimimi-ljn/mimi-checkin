import requests
import re
import ddddocr
from des import strEnc


def verify(username, password, timeout=10):
    session = requests.Session()

    # Step 1: Get IDM login page
    r = session.get(
        'https://idm.swu.edu.cn/am/UI/Login?service=initService&encoded=false',
        timeout=timeout
    )

    # Step 2: Extract hidden form fields
    random_val = re.search(r'name="random"\s+value="([^"]*)"', r.text)
    credence = re.search(r'name="credenceType"\s+value="([^"]*)"', r.text)
    sqp = re.search(r'name="SunQueryParamsString"\s+value="([^"]*)"', r.text)
    encoded = re.search(r'name="encoded"\s+value="([^"]*)"', r.text)
    charset = re.search(r'name="gx_charset"\s+value="([^"]*)"', r.text)
    goto = re.search(r'name="goto"\s+value="([^"]*)"', r.text)
    goto_fail = re.search(r'name="gotoOnFail"\s+value="([^"]*)"', r.text)

    if not random_val:
        return None

    random_key = random_val.group(1)

    # Step 3: Download CAPTCHA and OCR
    captcha_resp = session.get('https://idm.swu.edu.cn/am/validate.code', timeout=timeout)
    ocr = ddddocr.DdddOcr()
    validate_code = ocr.classification(captcha_resp.content)

    # Step 4: Encrypt credentials with random as key (browser does this in login.js)
    enc_user = strEnc(username, random_key, "", "")
    enc_pwd = strEnc(password, random_key, "", "")

    # Step 5: Submit login form
    data = {
        'IDToken1': enc_user,
        'IDToken2': enc_pwd,
        'IDToken3': '',
        'goto': goto.group(1) if goto else '',
        'gotoOnFail': goto_fail.group(1) if goto_fail else '',
        'SunQueryParamsString': sqp.group(1) if sqp else 'c2VydmljZT1pbml0U2VydmljZSY=',
        'encoded': encoded.group(1) if encoded else 'false',
        'gx_charset': charset.group(1) if charset else 'UTF-8',
        'credenceType': credence.group(1) if credence else 'COMMON',
        'random': random_key,
        'validateCode': validate_code,
    }
    response = session.post(
        'https://idm.swu.edu.cn/am/UI/Login',
        data=data,
        allow_redirects=False,
        timeout=timeout
    )
    if response.status_code != 302:
        return None
    return response
