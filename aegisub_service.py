#encoding:utf-8

import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
import json
import logging
import base64
logger = logging.Logger("MIN")
import subprocess
# async http call method
@gen.coroutine
def async_post(url, params=None, retjson=True, retcodesuccess=True, data=None, method='POST', headers=None,
               request_timeout=20, ensure_ascii=False):
    reqdata = json.dumps(params, ensure_ascii=ensure_ascii)

    if not headers:
        headers = {}
    headers['Xc-Src-Name'] = 'genass'
    # 正式环境
    try:
        http_client = AsyncHTTPClient()
        if method != 'GET':
            if data:
                response = yield http_client.fetch(url, method=method, body=data, headers=headers,
                                                   request_timeout=request_timeout)
            else:
                response = yield http_client.fetch(url, method=method, body=reqdata, headers=headers,
                                                   request_timeout=request_timeout)
        else:
            # GET method
            response = yield http_client.fetch(url, method=method, headers=headers, request_timeout=request_timeout)

    except Exception as e:
        raise gen.Return({'ret': -1, 'msg': str(e)})
    # check response
    if not response:
        raise gen.Return({'ret': -1, 'msg': 'not response'})

    try:
        # respdata = ujson.dumps(response)
        respdata = str(response)
    except Exception as e:
        raise gen.Return({'ret': -1, 'msg': str(e)})

    # check response code
    code = response.code
    if not code:
        logger.error('resp.code is None, url:%s, req:%s, resp:%s' % (url, reqdata, respdata))
        raise gen.Return({'ret': -1, 'msg': 'resp.code is None'})
    elif (code > 400) | (code < 100):
        logger.error('resp.code, url:%s, req:%s, code:%d, resp:%s' % (url, reqdata, code, respdata))
        raise gen.Return({'ret': -1, 'msg': 'code is %s' % code})
    elif code != 200:
        logger.warn('resp.code, url:%s, req:%s, code:%d, resp:%s' % (url, reqdata, code, respdata))

    # check response body
    respbody = response.body
    if not respbody:
        logger.error("resp.body is None, url:%s, req:%s, code:%d resp:%s" % (url, reqdata, code, respdata))
        raise gen.Return({'ret': -1, 'msg': 'resp.body is None'})

    # not check jsonformat and retcode
    if not retjson:
        raise gen.Return(respbody)

    # load response body to json
    try:
        body = json.loads(respbody)
        # log.info("resp.body: %s"%(ujson.dumps(body)))
        if not body:
            logger.error("resp.body loads is None, url:%s, req:%s, resp:%s" % (url, reqdata, respdata))
            raise gen.Return({'ret': -1, 'msg': 'resp.body loads is None'})
    except Exception as e:
        logger.warn("resp.body unmarshal error, url:%s, req:%s, respbody:%s, e:%s" % (url, reqdata, respbody, str(e)))
        raise gen.Return(respbody)

    # not check retcode success
    if not retcodesuccess:
        raise gen.Return(body)

    # get ret
    if body:
        pass
    else:
        body = dict()

    ret = body.get('ret', None)
    if not ret:
        ret = body.get('errcode', None)
        if not ret:
            body['ret'] = ret

    raise gen.Return(body)


@gen.coroutine
def upload_file(path, file_name):

    img_data = open(path, 'rb').read()
    url  = "http://opmedia.srv.in.ixiaochuan.cn/op/%s"


    if file_name.endswith('.gif'):
        url = url % 'save_gif'
    elif file_name.endswith('.jpg'):
        url = url % 'save_image'
    else:
        url = url % 'save_file'

    file_64 = base64.b64encode(img_data).decode('utf-8')

    params = {'file_data': file_64, 'buss_type': 'zuiyou_img', 'internal_token': '5b8f785cd50a7d40714ff76d01699688'}
    print(type(file_64))
    ret = yield async_post(url, params=params, headers={'Content-Type': 'application/json'})
    logger.info('img upload, ret:%s' % ret)
    raise gen.Return(ret)


class GenAssHandler(tornado.web.RequestHandler):

    @gen.coroutine
    def post(self):
        obj = json.loads(self.request.body)
        nickname = obj['nickname']
        ass_url = obj['ass_url']
        ass_body = yield async_post(ass_url, retjson=False, method='GET')
        ass_body = ass_body.decode('utf-8')
        
        ass_body = ass_body.replace('{__nickname__}', nickname)
        path_in = ass_url.split('/')[-1]
        open(path_in, 'wb').write(ass_body.encode('utf-8'))
        path_out = path_in + '_out.ass'
        subprocess.call(['src/aegisub',path_in,path_out])
        ret = yield upload_file(path_out, 'a.ass')
        self.jsonify(ret)

    def jsonify(self, response):
        response = json.dumps(response, ensure_ascii=False)
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.write(response)
        self.finish()

def make_app():
    return tornado.web.Application([
        (r"/genass", GenAssHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
