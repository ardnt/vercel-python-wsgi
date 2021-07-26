from werkzeug.wrappers import Request, Response


@Request.application
def application(request):
    traceback = request.args.get('traceback')
    if '_call_with_frames_removed' in traceback:
        traceback = traceback.split('_call_with_frames_removed')[1]
        traceback = traceback.replace('/var/task/', '')
        traceback = 'Traceback (most recent call last):' + traceback
    page = '''
<!DOCTYPE html>
<html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>Error in handler function</title>
<style type="text/css">
    html * {{ padding:0; margin:0; }}
    body * {{ padding:10px 20px; }}
    body * * {{ padding:0; }}
    body {{ font:small sans-serif; background-color:#fff; color:#000; }}
    body>div {{ border-bottom:1px solid #ddd; }}
    h1 {{ font-weight:normal; }}
    pre {{ font-size: 100%; white-space: pre-wrap; }}
    #summary {{ background: #ffc; }}
    #summary h2 {{ font-weight: normal; color: #666; }}
    pre.exception_value {{ font-family: sans-serif; color: #575757; font-size: 1.5em; margin: 10px 0 10px 0; }}
  </style>
</head>
<body>
<div id="summary">
  <h1>{0}</h1>
  <pre class="exception_value">{1}</pre>
</div>
</body></html>
'''.format(request.args.get('error'), traceback)
    return Response(page, mimetype='text/html')
