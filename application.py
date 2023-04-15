from aioflask import Flask, request, Response
from flask_cors import CORS
import jwt
from functools import wraps

import requests
import json
import asyncio

# Create the Flask application object.
app = Flask(__name__, template_folder="templates")
# NEVER HARDCODE YOUR CONFIGURATION IN YOUR CODE
# TODO: INSTEAD CREATE A .env FILE AND STORE IN IT
app.config['SECRET_KEY'] = 'longer-secret-is-better'
CORS(app)

courseurl = "http://ec2-3-83-221-153.compute-1.amazonaws.com:5011/course/"
coursepreference = "http://ec2-3-83-221-153.compute-1.amazonaws.com:5011/course/student_preference/"
studenturl = "http://ec2-54-161-242-249.compute-1.amazonaws.com:8000/students/"
teamurl = "http://ec2-3-84-34-200.compute-1.amazonaws.com:2233/team"


# decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # check jwt is passed in the request header
        if 'access-token' in request.headers:
            token = request.headers['access-token']
        if not token:
            return Response("TOKEN IS MISSING", status=401, content_type="text/plain")

        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
            uni, email = data['uni'], data['email']
        except:
            return Response("TOKEN IS INVALID", status=401, content_type="text/plain")
        # returns the current logged-in users contex to the routes
        return f(uni, email, *args, **kwargs)

    return decorated


async def get_profile(uni):
    profile_rsp = requests.session().get("http://ec2-54-161-242-249.compute-1.amazonaws.com:8000/students/" + "profile", json={"uni": uni})
    try:
        return profile_rsp.json()
    except:
        return False


async def get_course(id):
    courseurl = "http://ec2-3-83-221-153.compute-1.amazonaws.com:5011/courses/"
    course_rsp = requests.session().get(courseurl).json()
    for item in course_rsp:
        if item["Course_id"] == int(id):
            return True
    return False


def get_preference(uni, course_id):
    url = "http://ec2-3-83-221-153.compute-1.amazonaws.com:5011/course/student_preferences/uni=" + uni
    try:
        rsp_json = requests.session().get(url).json()
        print(rsp_json)
        for item in rsp_json:
            if item["Course_id"] == int(course_id):
                prefered_dept, prefered_timezone = item["prefered_Dept"], item["prefered_Timezone"]
                return [prefered_dept, prefered_timezone]
        return False
    except:
        return False


async def delete_preference(uni, course_id):
    url = "http://ec2-3-83-221-153.compute-1.amazonaws.com:5011/course/student_preference/delete/"
    rsp = requests.session().post(url, verify=False, json={'uni': uni, 'course_id': course_id})
    return rsp



@app.route("/", methods = ['GET'])
def init():
    return "hello world"

@app.route("/course/", methods=["GET"])
def get_course_by_name(course_name=""):
    if "course_name" in request.args:
        course_name = request.args["course_name"]
    rsp = requests.session().get(courseurl + '?course_name=' + course_name, verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response("NOT FOUND", status=404, content_type="text/plain")
    return rsp


@app.route("/course/add", methods=["POST"])
def insert_courses():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp

    course_name, department, introduction = request_data['course_name'], request_data['department'], request_data[
        'introduction']
    rsp = requests.session().post(courseurl + 'add', verify=False,
                                  json={'course_name': course_name, 'department': department,
                                        'introduction': introduction})
    if rsp.status_code == 200:
        rsp = Response("COURSE CREATED", status=200, content_type="text/plain")
    else:
        rsp = Response("There already exist one course", status=404, content_type="text/plain")
    return rsp


@app.route("/course/student_preference/add", methods=["POST"])
def add_course_preference():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    uni = request_data['uni']
    profile_rsp = requests.session().get("http://ec2-54-161-242-249.compute-1.amazonaws.com:8000/students/" + "profile", json={"uni": uni})
    try:
        profile_rsp = profile_rsp.json()
    except:
        return Response("You should first edit profile before you check or add preference", status=404,
                        content_type="text/plain")
    if profile_rsp['uni'] != uni:
        return Response("You should check or add your own preference", status=404, content_type="text/plain")
    uni, course_id, timezone, dept, message = request_data['uni'], request_data['course_id'], request_data['timezone'], \
                                              request_data['Dept'], request_data['message']
    rsp = requests.session().post(coursepreference + 'add', verify=False,
                                  json={'uni': uni, 'course_id': course_id, 'timezone': timezone, 'Dept': dept,
                                        'message': message})
    if rsp.status_code == 200:
        rsp = Response("Course Preferences CREATED", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/course/student_preference/", methods=["GET"])
def get_course_preference_by_uni(uni="", limit="", offset=""):
    if "uni" in request.args and "limit" in request.args and "offset" in request.args:
        uni, limit, offset = request.args["uni"], request.args["limit"], request.args["offset"]
    profile_rsp = requests.session().get("http://ec2-54-161-242-249.compute-1.amazonaws.com:8000/students/" + "profile", json={"uni": uni})
    try:
        profile_rsp = profile_rsp.json()
    except:
        return Response("You should first edit profile before you check or add preference", status=404,
                        content_type="text/plain")
    if profile_rsp['uni'] != uni:
        return Response("You should check or add your own preference", status=404, content_type="text/plain")
    rsp = requests.session().get(coursepreference + '?uni=' + uni + '&limit=' + limit + '&offset=' + offset,
                                 verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response("NOT FOUND", status=404, content_type="text/plain")
    return rsp


@app.route("/team/", methods=["get"])
def browse_all_team(course_id="", limit="", offset=""):
    if "course_id" in request.args and "limit" in request.args and "offset" in request.args:
        course_id, limit, offset = request.args["course_id"], request.args["limit"], request.args["offset"]
    rsp = requests.session().get(teamurl + '?course_id=' + course_id + '&limit=' + limit + '&offset=' + offset,
                                 verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/add/", methods=["POST", "GET"])
async def add_team():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    team_name, team_captain_uni, team_captain, course_id, number_needed, team_message = request_data['team_name'], \
                                                                                        request_data[
                                                                                            'team_captain_uni'], \
                                                                                        request_data['team_captain'], \
                                                                                        request_data['course_id'], \
                                                                                        request_data['number_needed'], \
                                                                                        request_data['team_message']
    loop = asyncio.get_event_loop()
    t1 = loop.create_task(get_profile(team_captain_uni))
    t2 = loop.create_task(get_course(course_id))
    t3 = loop.create_task(delete_preference(team_captain_uni, course_id))
    profile, id, delete = await asyncio.gather(t1, t2, t3)
    if not profile or not id:
        return Response("You may need profile or add the course", status=404, content_type="text/plain")
    rsp = requests.session().post(teamurl + '/add', verify=False,
                                  json={'team_name': team_name, 'team_captain_uni': team_captain_uni,
                                        'team_captain': team_captain, 'course_id': course_id,
                                        'number_needed': number_needed, 'team_message': team_message})
    if rsp.status_code == 200:
        rsp = Response("TEAM CREATED", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/edit/", methods=["POST", "GET"])
def edit_team():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    team_name, team_captain_uni, team_captain, course_id, number_needed, team_message = request_data['team_name'], \
                                                                                        request_data[
                                                                                            'team_captain_uni'], \
                                                                                        request_data['team_captain'], \
                                                                                        request_data['course_id'], \
                                                                                        request_data['number_needed'], \
                                                                                        request_data['team_message']
    rsp = requests.session().post(teamurl + '/edit', verify=False,
                                  json={'team_name': team_name, 'team_captain_uni': team_captain_uni,
                                        'team_captain': team_captain, 'course_id': course_id,
                                        'number_needed': number_needed, 'team_message': team_message})
    if rsp.status_code == 200:
        rsp = Response("TEAM EDITED", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/delete/", methods=["POST", "GET"])
def delete_team():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    team_captain_uni, course_id, team_id = request_data["team_captain_uni"], request_data["course_id"], request_data[
        "team_id"]
    rsp = requests.session().post(teamurl + '/delete', verify=False,
                                  json={'team_captain_uni': team_captain_uni,
                                        'course_id': course_id, 'team_id': team_id})
    if rsp.status_code == 200:
        rsp = Response("TEAM DELETED", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/team_member/", methods=["get"])
def browse_all_team_member(team_id="", course_id=""):
    if "course_id" in request.args and "team_id" in request.args:
        course_id, team_id = request.args['course_id'], request.args['team_id']
    rsp = requests.session().get(teamurl + '/team_member/?team_id=' + team_id + '&course_id=' + course_id, verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/info/", methods=["get"])
def browse_team_info_by_input(course_id="", team_captain_uni=""):
    if "course_id" in request.args and "team_captain_uni" in request.args:
        course_id, team_captain_uni = request.args['course_id'], request.args['team_captain_uni']
    rsp = requests.session().get(teamurl + '/info/?team_captain_uni=' + team_captain_uni + '&course_id=' + course_id,
                                 verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/add_member/", methods=["POST"])
async def add_team_member():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    uni, student_name, team_id, course_id = request_data["uni"], request_data["student_name"], request_data["team_id"], \
                                            request_data["course_id"]
    loop = asyncio.get_event_loop()
    t1 = loop.create_task(get_profile(uni))
    t2 = loop.create_task(delete_preference(uni, course_id))
    profile, delete = await asyncio.gather(t1, t2)
    print(profile)
    if not profile:
        return Response("The uni you add does not exist!", status=404, content_type="text/plain")
    rsp = requests.session().post(teamurl + '/add_member', verify=False,
                                  json={'uni': uni, 'student_name': student_name, 'team_id': team_id,
                                        'course_id': course_id})
    if rsp.status_code == 200:
        rsp = Response("Add Member successful!", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/delete_member/", methods=["POST"])
def delete_team_member():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    uni, team_id, course_id = request_data["uni"], request_data["team_id"], request_data["course_id"]
    rsp = requests.session().post(teamurl + '/delete_member', verify=False,
                                  json={'uni': uni, 'team_id': team_id,
                                        'course_id': course_id})
    if rsp.status_code == 200:
        rsp = Response("DELETE SUCCESS", status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/team/find_my_teammate/", methods=["get"])
def find_my_teammate(course_id="", uni=""):
    if "course_id" in request.args and "uni" in request.args:
        course_id, uni = request.args['course_id'], request.args['uni']
    preferences = get_preference(uni, course_id)
    if not preferences:
        return Response("No preference on this course has been found", status=404, content_type="text/plain")
    dept, timezone = preferences[0], preferences[1]
    rsp = requests.session().get(teamurl + '/find_my_teammate/?dept=' + dept + '&timezone=' + timezone, verify=False)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response(rsp.text, status=404, content_type="text/plain")
    return rsp


@app.route("/course/student_preference/edit/", methods=["GET", "POST"])
def edit_course_preference():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    uni, course_id, timezone, dept, messages = request_data['uni'], request_data['course_id'], request_data['timezone'], \
                                               request_data['Dept'], request_data['message']
    rsp = requests.session().post(coursepreference + 'edit', verify=False,
                                  json={'uni': uni, 'course_id': course_id, 'timezone': timezone, 'Dept': dept,
                                        'message': messages})
    if rsp.status_code == 200:
        rsp = Response("Course Preferences CREATED", status=200, content_type="text/plain")
    else:
        rsp = Response("The preference does not exist", status=404, content_type="text/plain")
    return rsp


@app.route("/course/student_preference/delete/", methods=["POST", "GET"])
def delete_course_preference_by_id_and_uni():
    if request.is_json:
        try:
            request_data = request.get_json()
        except ValueError:
            return Response("[COURSE] UNABLE TO RETRIEVE REQUEST", status=400, content_type="text/plain")
    else:
        return Response("[COURSE] INVALID POST FORMAT: SHOULD BE JSON", status=400, content_type="text/plain")
    if not request_data:
        rsp = Response("[COURSE] INVALID INPUT", status=404, content_type="text/plain")
        return rsp
    uni, course_id = request_data['uni'], request_data['course_id']
    rsp = requests.session().post(coursepreference + 'delete', verify=False, json={'uni': uni, 'course_id': course_id})
    if rsp.status_code == 200:
        rsp = Response("DELETE SUCCESS", status=200, content_type="application.json")
    else:
        rsp = Response("No existed Preference is found!", status=404, content_type="text/plain")
    return rsp


@app.route("/students/login", methods=['POST', 'GET'])
def login():
    request_data = request.get_json()
    uni, password = request_data['uni'], request_data['password']
    rsp = requests.session().post(studenturl + 'login', verify=False, json={'uni': uni, 'password': password})
    if rsp.status_code == 200:
        rsp_json = rsp.json()
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=rsp.status_code, content_type="text/plain")
    return rsp


@app.route("/students/account", methods=["POST"])
@token_required
def update_account_info(uni, email):
    request_data = request.get_json()
    uni, password = request_data['uni'], request_data['password']
    rsp = requests.session().post(studenturl + 'account', verify=False,
                                  json={'uni': uni, 'password': password, 'email': email}, headers=request.headers)
    rsp = Response(rsp.text, status=rsp.status_code, content_type="text/plain")
    return rsp


@app.route("/students/loginwithgoogle", methods=['GET', 'POST'])
def login_with_google():
    request_data = request.get_json()
    rsp = requests.session().post(studenturl + 'loginwithgoogle', verify=False, json=request_data)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="text/plain")
    else:
        rsp = Response(rsp.text, status=rsp.status_code, content_type="text/plain")
    return rsp


@app.route("/students/signup", methods=['POST'])
def signup():
    request_data = request.get_json()
    rsp = requests.session().post(studenturl + 'signup', verify=False, json=request_data)
    rsp = Response(rsp.text, status=rsp.status_code, content_type="text/plain")
    return rsp


@app.route("/students/account", methods=["GET"])
def get_student_by_input(uni="", email=""):
    if "uni" in request.args:
        uni = request.args["uni"]
    if "email" in request.args:
        email = request.args["email"]
    if uni != "" and email != "":
        rsp = requests.session().get(studenturl + 'account' + '?uni=' + uni + '&email=' + email, verify=False,
                                     headers=request.headers)
    elif uni != "":
        rsp = requests.session().get(studenturl + 'account' + '?uni=' + uni, verify=False, headers=request.headers)
    else:
        rsp = requests.session().get(studenturl + 'account' + '?email=' + email, verify=False, headers=request.headers)
    if rsp.status_code == 200:
        rsp = Response(json.dumps(rsp.json()), status=200, content_type="application.json")
    else:
        rsp = Response("NOT FOUND", status=401, content_type="text/plain")
    return rsp


@app.route("/students/profile", methods=["GET"])
@token_required
def get_profile_by_uni(uni, email):
    if uni == 'N/A':
        uni = email[:email.index('@')]
    rsp = requests.session().get(studenturl + 'profile', verify=False, json={"uni": uni}, headers=request.headers)
    if rsp.status_code == 404:
        return rsp.text
    else:
        return Response(json.dumps(rsp.json()), status=200, content_type="application.json")


@app.route("/students/profile", methods=["POST"])
@token_required
def update_profile(uni, email):
    request_data = request.get_json()
    if uni == 'N/A':
        uni = email[:email.index('@')]
    request_data['uni'], request_data['email'] = uni, email
    rsp = requests.session().post(studenturl + 'profile', verify=False, json=request_data, headers=request.headers)
    rsp = Response(rsp.text, status=rsp.status_code, content_type="text/plain")
    return rsp


@app.route("/students/resend", methods=["POST"])
def resend_confirmation():
    request_data = request.get_json()
    rsp = requests.session().post(studenturl + 'resend', verify=False, json=request_data)
    return rsp.text


app.run(host="0.0.0.0", port=10000)
    # app.run(ssl_context="adhoc")
