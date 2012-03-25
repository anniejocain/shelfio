from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from lil.shlvme.models import Shelf
import json
from django.core.context_processors import csrf
from django.contrib.auth.models import User

@csrf_exempt
def api_user(request, url_user_name):
    """API for users
     Accessed using something like shlv.me/api/user/obama
     TODO: we need to validate/clean/urldecode the GET/POST values ?
    """
    if request.method == 'GET':                
        context = _get_user_data(request, url_user_name)
        return HttpResponse(json.dumps(context, cls=DjangoJSONEncoder), mimetype='application/json')
    
    # If the user updates her profile, handle it here
    if (request.method == 'POST' or request.method == 'PATCH'):
        if not request.user.is_authenticated():
            return HttpResponse(status=401)
        elif request.user.username != url_user_name:
            return HttpResponse(status=403)

        try:
            _update_user_data(url_user_name, request.POST)
        except ValidationError, e:
            # Should an invalid update be a 400 (Bad Request) response?
            return HttpResponse(status=400)
        _get_user_data(request, url_user_name)
        return HttpResponse(json.dumps(context, cls=DjangoJSONEncoder), mimetype='application/json')

def user_home(request, user_name):
    """A user's home. Includes profile and list of shelves."""
    if request.method == 'GET':
        context = _get_user_data(request, user_name)
        context['user'] = request.user
        context.update(csrf(request))
        return render_to_response('user/show.html', context)

    elif request.method == 'POST' and request.POST.get('_method').upper() == 'PATCH':
        if not request.user.is_authenticated():
            return HttpResponse(status=401)
        elif user_name != request.user.username:
            return HttpResponse(status=403)

        try:
            _update_user_data(user_name, request.POST)
        except ValidationError, e:
            return HttpResponse(status=400)
        return redirect(reverse('user_home', args=[user_name]))

def _get_user_data(request, user_name):
    context = {}
    target_user = get_object_or_404(User, username=user_name)
    queried_shelves = Shelf.objects.filter(user=target_user)
    is_owner = target_user.username == request.user.username and request.user.is_authenticated()
    shelf_query = Shelf.objects.filter(user=target_user)
    shelves = []
    
    if is_owner:
        context.update({
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'date_joined': target_user.date_joined,
            'email': target_user.email
        })
    else:
        shelf_query.exclude(is_public=True)

    for shelf in shelf_query:
        shelf_to_serialize = {
            'shelf_uuid': str(shelf.shelf_uuid),
            'name': shelf.name,
            'description': shelf.description,
            'creation_date': shelf.creation_date,
            'is_public': shelf.is_public
        }
        shelves.append(shelf_to_serialize)

    context.update({
        'is_owner': is_owner,
        'user_name': target_user.username,
        'docs': shelves
    })

    return context

def _update_user_data(user_name, updates):
    target_user = get_object_or_404(User, username=user_name)
    updatables = ['first_name', 'last_name', 'email']
    for key in updatables:
        setattr(target_user, key, updates[key])
    target_user.full_clean()
    target_user.save()