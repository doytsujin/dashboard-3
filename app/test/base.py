import warnings

from flask import Flask
from flask_testing import TestCase

from models import db, Application, Service, Evaluation, EvaluationResult, User, ApplicationUserRole, Role
from app import initialize_app


class BaseTestCase(TestCase):
    def create_app(self):
        app = Flask(__name__)
        initialize_app(app, {})
        return app

    @classmethod
    def setUpClass(cls):
        warnings.filterwarnings("ignore",
                                category=ImportWarning,
                                message="can't resolve package from __spec__ or __package__, falling back on __name__ and __path__")

    def setUp(self):
        db.create_all()
        aobj = create_app_obj(save=True)
        create_service_obj(aobj.application_id, save=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()


def create_app_obj(kubernetes_id=1, save=False):
    app_name = 'drucker-test-app'
    aobj = Application(application_name=app_name, kubernetes_id=kubernetes_id)
    aobj_ = Application.query.filter_by(
        application_name=app_name,
        kubernetes_id=kubernetes_id).one_or_none()
    if save and aobj_ is None:
        db.session.add(aobj)
        db.session.commit()
        return aobj
    else:
        return aobj_


def create_service_obj(
        application_id,
        model_id=3,
        service_name='drucker-test-app-development-20180628151929',
        service_level='development',
        host='localhost:5000',
        save=False):
    sobj = Service(application_id=application_id,
                   service_name=service_name,
                   service_level=service_level,
                   host=host,
                   model_id=model_id,
                   display_name=service_name)
    sobj_ = Service.query.filter_by(
        service_name=service_name).one_or_none()
    if save and sobj_ is None:
        db.session.add(sobj)
        db.session.commit()
        return sobj
    else:
        return sobj_


def create_eval_obj(
        application_id,
        checksum='abcde',
        data_path='my_data_path',
        save=False):
    eobj = Evaluation(checksum=checksum,
                      application_id=application_id,
                      data_path=data_path)
    if save:
        db.session.add(eobj)
        db.session.commit()
    return eobj


def create_eval_result_obj(
        model_id,
        evaluation_id,
        data_path='my_data_path',
        result='{}',
        save=False):
    robj = EvaluationResult(model_id=model_id,
                            data_path='my_result_path',
                            evaluation_id=evaluation_id,
                            result=result)
    if save:
        db.session.add(robj)
        db.session.commit()
    return robj


def create_user_obj(auth_id, user_name, save=False):
    uobj = User(auth_id=auth_id, user_name=user_name)
    uobj_ = User.query.filter_by(auth_id=auth_id).one_or_none()
    if save and uobj_ is None:
        db.session.add(uobj)
        db.session.commit()
        return uobj
    else:
        return uobj_


def create_application_user_role_obj(application_id, user_id, role=Role.viewer, save=True):
    robj = ApplicationUserRole(application_id=application_id, user_id=user_id, role=role)
    robj_ = ApplicationUserRole.query.filter_by(application_id=application_id, user_id=user_id).one_or_none()
    if save and robj_ is None:
        db.session.add(robj)
        db.session.commit()
        return robj
    else:
        robj_.role = role
        return robj_
