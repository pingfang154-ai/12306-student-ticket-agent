# -*- coding: utf-8 -*-
import urllib.request, urllib.parse
BASE='http://127.0.0.1:8085/check'
def check(school, home, dep, arr, via=None):
    q={'school':school,'home':home,'dep':dep,'arr':arr}
    if via: q['waypoints']=via
    url=BASE+'?'+urllib.parse.urlencode(q)
    try:
        html=urllib.request.urlopen(url, timeout=20).read().decode('utf-8','ignore')
    except Exception as e:
        return 'ERR '+str(e)
    ok = ('✅' in html) or ('符合' in html) or ('可购买' in html)
    # extract a short verdict snippet
    import re
    m=re.search(r'(符合优惠区间|不符合优惠区间|全程均可购买学生票|合规|不合规)', html)
    verdict = m.group(1) if m else '(no keyword)'
    return ('OK' if ok else 'NO')+' :: '+verdict
print('1) 南昌→福州:', check('南昌市','福州市','南昌西站','福州南站'))
print('2) 赣州→厦门:', check('赣州市','厦门市','赣州站','厦门北站'))
print('3) 赣州→福州 via南昌:', check('赣州市','福州市','赣州站','福州南站','南昌西站'))
print('4) 抚州→南昌(同城/邻):', check('抚州市','南昌市','抚州站','南昌西站'))
print('5) 龙岩→福州:', check('龙岩市','福州市','龙岩站','福州站'))
