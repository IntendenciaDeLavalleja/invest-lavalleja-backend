"""The console can bootstrap either administrator profile with the Buzón CLI syntax."""
import re
import time

import pytest

from gianna import create_app
from gianna.security import totp


PASSWORD='a-long-cli-test-password'


@pytest.fixture
def app(cfg):
    result=create_app(cfg)
    result.config['TESTING']=True
    return result


@pytest.mark.parametrize('flag,role',[
    ('true','owner'),('false','editor'),('TRUE','owner'),('False','editor'),(None,'editor'),
])
def test_create_admin_buzon_syntax(app,flag,role):
    args=['create-admin','Nombre de prueba','CLI@Example.Test',PASSWORD]
    if flag is not None:args.append(flag)
    result=app.test_cli_runner().invoke(args=args)
    assert result.exit_code==0,result.output
    s=app.extensions['gianna']
    user=s.db.one('SELECT * FROM users WHERE email=?',('cli@example.test',))
    assert user['role']==role and user['active']==1 and user['mfa_enrolled']==0
    assert user['mfa_method']=='totp' and user['name']=='Nombre de prueba'
    assert s.security.begin_login('cli@example.test',PASSWORD,'127.0.0.1')[1]=='enroll'
    assert PASSWORD not in result.output


@pytest.mark.parametrize('flag,status', [('true',200),('false',403)])
def test_created_account_obeys_superadmin_permissions_after_mfa(app,flag,status):
    result=app.test_cli_runner().invoke(args=['create-admin','Cuenta CLI','cli@example.test',PASSWORD,flag])
    assert result.exit_code==0,result.output
    s=app.extensions['gianna'];client=app.test_client()
    page=client.get('/admin/login')
    left,right=map(int,re.search(r'(\d+) \+ (\d+)',page.get_data(as_text=True)).groups())
    with client.session_transaction(path='/admin/login') as session:csrf=session['csrf']
    login=client.post('/admin/login',data={'email':'cli@example.test','password':PASSWORD,
        'csrf':csrf,'captcha':str(left+right)})
    assert login.status_code==302 and login.location.endswith('/admin/mfa')
    with client.session_transaction(path='/admin/mfa') as session:
        pending=session['pending'];csrf=session['csrf']
    challenge=s.security.challenge_info(pending)
    secret=s.security.unseal(challenge['secret'])
    assert client.post('/admin/mfa',data={'csrf':csrf,'code':totp(secret,int(time.time()//30))}).status_code==200
    assert client.get('/admin/dashboard').status_code==200
    assert client.get('/admin/users').status_code==status
    assert client.get('/admin/settings').status_code==status
    with client.session_transaction(path='/admin/users') as session:csrf=session['csrf']
    response=client.post('/admin/users',data={'csrf':csrf,'name':'Otro','email':'other@example.test','role':'editor'})
    assert response.status_code==status


def test_invalid_boolean_and_duplicate_do_not_create_or_promote_users(app):
    runner=app.test_cli_runner()
    assert runner.invoke(args=['create-admin','Admin','cli@example.test',PASSWORD,'false']).exit_code==0
    invalid=runner.invoke(args=['create-admin','Otra','bad@example.test',PASSWORD,'yes'])
    assert invalid.exit_code!=0 and app.extensions['gianna'].db.one('SELECT id FROM users WHERE email=?',('bad@example.test',)) is None
    duplicate=runner.invoke(args=['create-admin','Superadmin','CLI@example.test','another-long-password','true'])
    assert duplicate.exit_code==1 and 'Ya existe una cuenta' in duplicate.output
    user=app.extensions['gianna'].db.one('SELECT role,name FROM users WHERE email=?',('cli@example.test',))
    assert user=={'role':'editor','name':'Admin'}
    assert PASSWORD not in invalid.output+duplicate.output
