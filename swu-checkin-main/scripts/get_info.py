import json
import requests
import urllib.parse
import re
import ddddocr
from des import strEnc
from verify import verify


def get_token(username: str, password: str, timeout=10):
    def transform(ticket):
        ST = urllib.parse.unquote(ticket)
        ticket = urllib.parse.unquote(ticket).split("-")
        str1 = ""
        str2 = ""
        for i in ticket[1]:
            str1 += str((int(i) + 5) % 10)
        for i in ticket[2]:
            if "0" <= i <= "9":
                str2 += str((int(i) + 5) % 10)
            elif 'A' <= i <= 'Z':
                if ord(i) + 10 > ord('Z'):
                    str2 += chr(ord(i) + 10 - 26)
                else:
                    str2 += chr(ord(i) + 10)
            else:
                if ord(i) + 15 > ord('z'):
                    str2 += chr(ord(i) + 15 - 26)
                else:
                    str2 += chr(ord(i) + 15)
        return str1, str2

    session = requests.Session()

    # Step 1: Get state from the OAuth redirect chain
    initial_url = (
        'https://of.swu.edu.cn/cas/oauth/login/SWU_CAS2_FEDERAL'
        '?service=https%3A%2F%2Fof.swu.edu.cn%2Fgateway%2Ffighter-middle%2Fapi%2Fintegrate%2Fuaap%2Fcas%2Fresolve-cas-return'
        '%3Fnext%3Dhttps%253A%252F%252Fof.swu.edu.cn%252F%2523%252FcasLogin%253Ffrom%253D%25252FappCenter'
    )
    r = session.get(initial_url, timeout=timeout, allow_redirects=True)

    # Step 2: The redirect lands on CAS login page. Extract state from originalRequestUrl.
    decoded_url = urllib.parse.unquote(urllib.parse.unquote(r.url))
    if 'state=' not in decoded_url:
        raise Exception("登录失败：无法获取state参数")
    state = decoded_url.split('state=')[1][0:32]

    # Step 3: Redirect from CAS to IDM via federalEnable=true (bypasses slider CAPTCHA)
    sep = '&' if '?' in r.url else '?'
    idm_url = r.url + sep + 'federalEnable=true'
    r_idm = session.get(idm_url, timeout=timeout, allow_redirects=True)
    if 'idm.swu.edu.cn' not in r_idm.url:
        raise Exception("登录失败：无法跳转到IDM登录页")

    # Step 4: Extract hidden form fields from IDM page
    random_val = re.search(r'name="random"\s+value="([^"]*)"', r_idm.text)
    if not random_val:
        raise Exception("登录失败：无法获取CSRF令牌")
    random_key = random_val.group(1)
    sqp = re.search(r'name="SunQueryParamsString"\s+value="([^"]*)"', r_idm.text)
    encoded = re.search(r'name="encoded"\s+value="([^"]*)"', r_idm.text)
    charset = re.search(r'name="gx_charset"\s+value="([^"]*)"', r_idm.text)
    credence = re.search(r'name="credenceType"\s+value="([^"]*)"', r_idm.text)
    goto = re.search(r'name="goto"\s+value="([^"]*)"', r_idm.text)
    goto_fail = re.search(r'name="gotoOnFail"\s+value="([^"]*)"', r_idm.text)

    # Step 5: Download CAPTCHA and OCR
    captcha_resp = session.get('https://idm.swu.edu.cn/am/validate.code', timeout=timeout)
    ocr = ddddocr.DdddOcr()
    validate_code = ocr.classification(captcha_resp.content)

    # Step 6: Encrypt credentials with random as key (browser does this in login.js)
    enc_user = strEnc(username, random_key, "", "")
    enc_pwd = strEnc(password, random_key, "", "")

    # Step 7: Submit IDM login
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
    login_resp = session.post(
        'https://idm.swu.edu.cn/am/UI/Login',
        data=data,
        allow_redirects=False,
        timeout=timeout
    )

    if login_resp.status_code != 302:
        raise Exception("登录失败：账号或密码错误，或验证码识别失败")

    # Step 8: Follow the redirect after IDM login
    next_url = login_resp.headers.get('Location', '')
    if not next_url:
        raise Exception("登录失败：无法获取重定向地址")

    # Follow redirects step by step to find the ticket
    for _ in range(10):
        resp = session.get(next_url, allow_redirects=False, timeout=timeout)
        if resp.status_code != 302:
            break
        next_url = resp.headers.get('Location', '')
        if not next_url:
            break
        # Check for ticket in the URL
        if 'ticket=' in next_url:
            ticket = next_url.split('ticket=')[1].split('&')[0]
            str1, str2 = transform(ticket)
            CD = f"CD-{str1}-{str2}-wiie://777.643.675.751:3537/rph"
            callback_url = urllib.parse.unquote(
                f"https://of.swu.edu.cn/cas/oauth/callback/SWU_CAS2_FEDERAL?code={CD}@@hxbeat&state={state}"
            )
            cb_resp = session.get(callback_url, allow_redirects=True, timeout=timeout)
            if 'ticket=' not in cb_resp.url:
                raise Exception("登录失败：无法获取ST参数")
            ST = cb_resp.url.split('ticket=')[1].split('&')[0]
            token_resp = requests.get(
                f'https://of.swu.edu.cn/gateway/fighter-middle/api/integrate/uaap/cas/exchange-token?token={ST}&remember=true',
                timeout=timeout
            ).json()
            if 'data' in token_resp:
                return token_resp['data']
            break

    raise Exception("登录失败：无法获取访问令牌")


def get_student_id(token, timeout=10):
    url = "https://of.swu.edu.cn/gateway/fighter-middle/api/auth/user?appType=fighter-portal"
    headers = {"fighter-auth-token": token}
    student_id = requests.get(url, headers=headers, timeout=timeout).json()["data"]["subject"]["username"]
    return student_id


def get_dormitory(token, timeout=10):
    url = "https://of.swu.edu.cn/gateway/fighter-baida/api/cqlc/getDormitory"
    headers = {"fighter-auth-token": token, "Content-Type": "application/json;charset=UTF-8"}
    response = requests.post(url, headers=headers, data=json.dumps({}), timeout=timeout)
    return response.json()


def get_transition_today(token, timeout=10):
    url = "https://of.swu.edu.cn/gateway/fighter-baida/api/cqtj/getTransitionByToday"
    headers = {"fighter-auth-token": token}
    data = {"pageNum": 1, "pageSize": 1}
    response = requests.post(url, headers=headers, data=data, timeout=timeout).json()["data"]["records"]
    return response[0] if response else None
