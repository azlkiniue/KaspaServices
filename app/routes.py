from app import app, auth, session
from app.models import User, Sensor
from flask import request, abort, jsonify, g, send_from_directory
from cassandra.query  import SimpleStatement
from flask_httpauth import HTTPBasicAuth
import os, tarfile

@app.route('/')
@app.route('/index')
@auth.login_required
def index():
    return "index"

@app.route('/api/token/v1.0/getauthtoken', methods=['GET'])
@auth.login_required
def getauthtoken():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})

@app.route('/api/sensors/v1.0/downloadinstaller', methods=['GET'])
def downloadinstaller():
    filename = 'installer.sh'
    filedir = app.config['BASEDIR'] + '/app/static/'

    return send_from_directory(filedir, filename, as_attachment=True)

@app.route('/api/sensors/v1.0/verifysensorkey', methods=['POST'])
@auth.login_required
def verifysensorkey():
    device_id = request.json.get('device_id')
    sensor_key = request.json.get('sensor_key')
    netint = request.json.get('netint')
    if device_id is None or sensor_key is None or netint is None:
        abort(400)
    q = Sensor.objects.filter(company = g.user['company'])
    q = q.filter(device_id = device_id)
    sensor = q.first()

    if sensor is None:
        abort(400)

    #create tarball

    buildfile = 'build_snoqtt.sh'
    conffile = 'env-conf.conf'
    removefile = 'remove_snoqtt.sh'
    startfile = 'start_snoqtt.sh'
    stopfile = 'stop_snoqtt.sh'
    
    filedirtemplate = app.config['BASEDIR'] + '/app/static/template/'
    
    if not os.path.exists(app.config['BASEDIR'] + '/app/static/generated/{}/'.format(sensor_key)):
        os.makedirs(app.config['BASEDIR'] + '/app/static/generated/{}/'.format(sensor_key))
    
    filediroutput = app.config['BASEDIR'] + '/app/static/generated/{}/'.format(sensor_key)

    with open(filedirtemplate + buildfile) as build_template:
        templatebuild = build_template.read()
    with open(filediroutput + buildfile, "w") as current:
        current.write(templatebuild.format(protected_subnet=sensor['protected_subnet'],
                                            external_subnet=sensor['external_subnet'],
                                            oinkcode=sensor['oinkcode']))
    
    with open(filedirtemplate + conffile) as conf_template:
        templateconf = conf_template.read()
    with open(filediroutput + conffile, "w") as current:
        current.write(templateconf.format(global_topic=sensor['topic_global'],
                                            global_server='103.24.56.244',
                                            global_port='1883',
                                            device_id=sensor['device_id'],
                                            oinkcode=sensor['oinkcode'],
                                            protected_subnet=sensor['protected_subnet'],
                                            external_subnet=sensor['external_subnet'],
                                            netint=netint,
                                            company=g.user['company']))
    
    with open(filedirtemplate + removefile) as remove_template:
        templateremove = remove_template.read()
    with open(filediroutput + removefile, "w") as current:
        current.write(templateremove)

    with open(filedirtemplate + startfile) as start_template:
        templatestart = start_template.read()
    with open(filediroutput + startfile, "w") as current:
        current.write(templatestart)

    with open(filedirtemplate + stopfile) as stop_template:
        templatestop = stop_template.read()
    with open(filediroutput + stopfile, "w") as current:
        current.write(templatestop)

    filetarname='snoqtt-{}.tar.gz'.format(sensor_key)
    if os.path.exists(filediroutput + filetarname):
        os.remove(filediroutput + filetarname)

    tar = tarfile.open((filediroutput + filetarname), "w:gz")
    tar.add(filediroutput + buildfile, arcname=buildfile)
    tar.add(filediroutput + conffile, arcname=conffile)
    tar.add(filediroutput + removefile, arcname=removefile)
    tar.add(filediroutput + startfile, arcname=startfile)
    tar.add(filediroutput + stopfile, arcname=stopfile)
    tar.close()

    os.remove(filediroutput + buildfile)
    os.remove(filediroutput + conffile)
    os.remove(filediroutput + removefile)
    os.remove(filediroutput + startfile)
    os.remove(filediroutput + stopfile)

    return send_from_directory(filediroutput, filetarname, as_attachment=True)

@app.route('/api/sensors/v1.0/listsensors', methods=['POST'])
@auth.login_required
def listsensors():
    company = g.user['company']
    if company is None:
        abort(400)
    
    obj={
        "company" : g.user['company'],
        "count" : 0,
        "sensors" : []
    }
    for sensor in Sensor.objects.filter(company=company):
        sensor_obj = {
            "device_id" : sensor['device_id'],
            "device_name" : sensor['device_name'],
            "hostname" : sensor['hostname'],
            "ip_address" : sensor['ip_address'],
            "location" : sensor['location'],
            "protected_subnet" : sensor['protected_subnet'],
            "external_subnet" : sensor['external_subnet'],
            "oinkcode" : sensor['oinkcode'],
            "topic_global" : sensor['topic_global'],
            "topic_cmd" : sensor['topic_cmd'],
            "topic_resp" : sensor['topic_resp'],
            "sensor_key" : sensor['sensor_key'],
            "time_created" : sensor['time_created']
        }
        obj['sensors'].append(sensor_obj)
        obj['count'] = obj['count'] + 1
    
    return jsonify(obj)

@app.route('/api/sensors/v1.0/getsensordetail', methods=['POST'])
@auth.login_required
def getsensordetail():
    company = g.user['company']
    device_id = request.json.get('device_id')
    if device_id is None or company is None:
        abort(400)
    
    q = Sensor.objects.filter(company=company)
    q = q.filter(device_id=device_id)
    sensor = q.first()

    if sensor is None:
        abort(400)
    
    sensor_obj = {
        "company" : sensor['company'],
        "device_id" : sensor['device_id'],
        "device_name" : sensor['device_name'],
        "hostname" : sensor['hostname'],
        "ip_address" : sensor['ip_address'],
        "location" : sensor['location'],
        "protected_subnet" : sensor['protected_subnet'],
        "external_subnet" : sensor['external_subnet'],
        "oinkcode" : sensor['oinkcode'],
        "topic_global" : sensor['topic_global'],
        "topic_cmd" : sensor['topic_cmd'],
        "topic_resp" : sensor['topic_resp'],
        "sensor_key" : sensor['sensor_key'],
        "time_created" : sensor['time_created']
    }
    
    return jsonify(sensor_obj)

@app.route('/api/sensors/v1.0/createsensor', methods=['POST'])
@auth.login_required
def createsensor():
    device_name = request.json.get('device_name')
    hostname = request.json.get('hostname')
    ip_address = request.json.get('ip_address')
    location = request.json.get('location')
    protected_subnet = request.json.get('protected_subnet')
    external_subnet = request.json.get('external_subnet')
    oinkcode = request.json.get('oinkcode')
    company = g.user['company']
    sensor = Sensor(company=company, device_name=device_name,
        hostname=hostname, ip_address=ip_address, location=location,
        protected_subnet=protected_subnet)
    
    if external_subnet:
        sensor.set_oinkcode(oinkcode)
    if external_subnet:
        sensor.set_external_subnet(external_subnet)

    sensor.create_dev_id(device_name)
    sensor.create_topic_cmd()
    sensor.create_topic_resp()

    Sensor.create(company=sensor['company'],
        device_id=sensor['device_id'],
        device_name=sensor['device_name'],
        hostname=sensor['hostname'],
        ip_address=sensor['ip_address'],
        location=sensor['location'],
        protected_subnet=sensor['protected_subnet'],
        external_subnet=sensor['external_subnet'],
        oinkcode=sensor['oinkcode'],
        topic_global=sensor['topic_global'],
        topic_cmd=sensor['topic_cmd'],
        topic_resp=sensor['topic_resp'],
        sensor_key=sensor['sensor_key'],
        time_created=sensor['time_created']
    )

    return jsonify({
        'device_id' : sensor['device_id'],
        'device_name' : sensor['device_name'],
        'sensor_key' : sensor['sensor_key'],
    })

@app.route('/api/users/v1.0/getuserdetail/<username>', methods=['GET'])
@auth.login_required
def getuserdetail(username):
    q = User.objects.filter(username=username).first()
    if User.objects.filter(username = username).first() is None:
        abort(400)
    username = q['username']
    first_name = q['first_name']
    last_name = q['last_name']
    email = q['email']
    company = q['company']

    return jsonify({
        'username' : username,
        'first_name' : first_name,
        'last_name' : last_name,
        'email' : email,
        'company' : company
    })

@app.route('/api/users/v1.0/createuser', methods=['POST'])
def createuser():
    username = request.json.get('username')
    password = request.json.get('password')
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    email = request.json.get('email')
    company = request.json.get('company')
    if username is None or password is None:
        abort(400)
    if User.objects.filter(username = username).first() is not None:
        abort(400)
    user = User(username = username, first_name = first_name, last_name = last_name, email = email, company = company)
    user.hash_password(password)
    user.set_admin()

    User.create(username=user['username'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        password_hash=user['password_hash'],
        email=user['email'],
        company=user['company'],
        group=user['group'],
        time_joined=user['time_joined']
    )

    return jsonify({'username': user['username']}), 201

@app.route('/api/statistic/v1.0/rawdata', methods=['POST'])
@auth.login_required
def getrawdata():
    # company = g.user['company']
    company = request.json.get('company')
    year = request.json.get('year')
    month = request.json.get('month')
    day = request.json.get('day')
    hour = request.json.get('hour')
    minute = request.json.get('minute')
    second = request.json.get('second')

    query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}'".format(company)
    if year is not None:
        query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={}".format(
            company, year
        )
        if month is not None:
            query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={} and month={}".format(
                company, year, month
            )
            if day is not None:
                query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={} and month={} and day={}".format(
                    company, year, month, day
                )
                if hour is not None:
                    query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={} and month={} and day={} and hour={}".format(
                        company, year, month, day, hour
                    )
                    if minute is not None:
                        query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={} and month={} and day={} and hour={} and minute={}".format(
                            company, year, month, day, hour, minute
                        )
                        if second is not None:
                            query = "SELECT * FROM kaspa.raw_data_by_company WHERE company='{}' and year={} and month={} and day={} and hour={} and minute={} and second={}".format(
                                company, year, month, day, hour, minute, second
                            )

    statement = SimpleStatement(query)
    obj = {
        "company" : company,
        "count" : 0,
        "data" : []
    }
    for raw_data in session.execute(statement):
        obj['data'].append(raw_data)
        obj['count'] = obj['count'] + 1
    
    return jsonify(obj)

@auth.verify_password
def verify_password(username_or_token, password):
    user = User.verify_auth_token(username_or_token)
    if not user:
        user = User.objects.filter(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True