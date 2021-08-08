from werkzeug.wrappers import Request, Response
from werkzeug import Template


@Request.application
def application(request):
    frames = request.args.get('frames')
    # if '_call_with_frames_removed' in traceback:
    #     traceback = traceback.split('_call_with_frames_removed')[-1]
    #     traceback = traceback.replace('/var/task/', '')
    #     traceback = 'Traceback (most recent call last):' + traceback
    template = Template.from_file('500.html')
    context = {
        # 'error': request.args.get('error'),
        'lastframe': frames[-1],
        'frames': frames,
    }
    # .format(request.args.get('error'), traceback)
    return Response(template.render(**context), mimetype='text/html')
