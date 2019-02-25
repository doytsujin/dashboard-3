import uuid

from flask_restplus import Namespace, fields, Resource, reqparse
from flask_jwt_simple import get_jwt_identity

from werkzeug.datastructures import FileStorage

from . import (
    api, DatetimeToTimestamp, status_model, update_kubernetes_deployment_info,
    save_kubernetes_access_file, remove_kubernetes_access_file, backup_kubernetes_deployment
)
from rekcurd_dashboard.models import db, KubernetesModel, ProjectUserRoleModel, ProjectRole, ApplicationModel, ServiceModel
from rekcurd_dashboard.utils import ProjectUserRoleException


kubernetes_api_namespace = Namespace('kubernetes', description='Kubernetes API Endpoint.')
success_or_not = kubernetes_api_namespace.model('Success', status_model)
kubernetes_model_params = kubernetes_api_namespace.model('Kubernetes', {
    'kubernetes_id': fields.Integer(
        readOnly=True,
        description='Kubernetes cluster ID.'
    ),
    'project_id': fields.Integer(
        readOnly=True,
        description='Project ID.'
    ),
    'display_name': fields.String(
        required=True,
        description='DisplayName.',
        example='cluster-1'
    ),
    'description': fields.String(
        required=False,
        description='Description.',
        example='This is a sample.'
    ),
    'config_path': fields.String(
        readOnly=True,
        description='Kubernetes configuration file path.',
        example='/kube-config/kube-1.config'
    ),
    'ingress_host': fields.String(
        required=True,
        description='Ingress host or External IP.',
        example='127.0.0.1'
    ),
    'ingress_port': fields.Integer(
        required=True,
        description='Ingress port or NodePort.',
        example='33000'
    ),
    'register_date': DatetimeToTimestamp(
        readOnly=True,
        description='Register date.'
    )
})


@kubernetes_api_namespace.route('/projects/<int:project_id>/kubernetes')
class ApiKubernetes(Resource):
    kubernetes_model_parser = reqparse.RequestParser()
    kubernetes_model_parser.add_argument(
        'file', location='files', type=FileStorage, required=True,
        help='Kubernetes access_token configuration file.')
    kubernetes_model_parser.add_argument(
        'display_name', location='form', type=str, required=True,
        help="Must be unique. If empty, automatically generated.")
    kubernetes_model_parser.add_argument(
        'description', location='form', type=str, required=False,
        help='Description.')
    kubernetes_model_parser.add_argument(
        'ingress_host', location='form', type=str, required=True,
        help='Ingress host or External IP. e.g. "127.0.0.1", "example.com"')
    kubernetes_model_parser.add_argument(
        'ingress_port', location='form', type=int, required=True,
        help='Ingress port or NodePort. e.g. "33000"')

    @kubernetes_api_namespace.marshal_list_with(kubernetes_model_params)
    def get(self, project_id: int):
        """get_kubernetes"""
        if api.dashboard_config.IS_ACTIVATE_AUTH:
            user_id = get_jwt_identity()
            role: ProjectUserRoleModel = db.session.query(ProjectUserRoleModel).filter(
                ProjectUserRoleModel.project_id == project_id,
                ProjectUserRoleModel.user_id == user_id).one_or_none()
            if role is None or role.project_role != ProjectRole.admin:
                raise ProjectUserRoleException("Invalid access.")
        return KubernetesModel.query.filter_by(project_id=project_id).all()

    @kubernetes_api_namespace.marshal_with(success_or_not)
    def put(self, project_id: int):
        """update to the latest Kubernetes deployment info."""
        kubernetes_model = KubernetesModel.query.filter_by(project_id=project_id).first()
        update_kubernetes_deployment_info(kubernetes_model)
        db.session.commit()
        db.session.close()
        response_body = {"status": True, "message": "Success."}
        return response_body

    @kubernetes_api_namespace.marshal_with(success_or_not)
    @kubernetes_api_namespace.expect(kubernetes_model_parser)
    def post(self, project_id: int):
        """add_kubernetes"""
        args = self.kubernetes_model_parser.parse_args()
        config_path = "{0}.config".format(uuid.uuid4().hex)
        file = args['file']
        display_name = args['display_name']
        description = args['description']
        ingress_host = args['ingress_host']
        ingress_port = args['ingress_port']
        kubernetes_model = KubernetesModel(
            project_id=project_id, display_name=display_name, description=description,
            config_path=config_path, ingress_host=ingress_host, ingress_port=ingress_port)
        db.session.add(kubernetes_model)
        db.session.flush()
        save_kubernetes_access_file(file, config_path)
        try:
            update_kubernetes_deployment_info(kubernetes_model)
            db.session.commit()
            db.session.close()
            response_body = {"status": True, "message": "Success."}
        except Exception as error:
            remove_kubernetes_access_file(config_path)
            raise error
        return response_body


@kubernetes_api_namespace.route('/projects/<int:project_id>/backup')
class ApiKubernetesBackup(Resource):
    @kubernetes_api_namespace.marshal_with(success_or_not)
    def post(self, project_id: int):
        """backup Kubernetes deployment"""
        kubernetes_models = KubernetesModel.query.filter_by(project_id=project_id).all()
        if kubernetes_models:
            kubernetes_model = kubernetes_models[0]
            for application_model in ApplicationModel.query.filter_by(project_id=project_id).all():
                for service_model in ServiceModel.query.filter_by(application_id=application_model.application_id).all():
                    backup_kubernetes_deployment(kubernetes_model, application_model, service_model)
        response_body = {"status": True, "message": "Success."}
        return response_body


@kubernetes_api_namespace.route('/projects/<int:project_id>/kubernetes/<int:kubernetes_id>')
class ApiKubernetesId(Resource):
    kubernetes_model_parser = reqparse.RequestParser()
    kubernetes_model_parser.add_argument(
        'file', location='files', type=FileStorage, required=False,
        help='Kubernetes access_token configuration file.')
    kubernetes_model_parser.add_argument(
        'display_name', location='form', type=str, required=False,
        help="Must be unique. If empty, automatically generated.")
    kubernetes_model_parser.add_argument(
        'description', location='form', type=str, required=False,
        help='Description.')
    kubernetes_model_parser.add_argument(
        'ingress_host', location='form', type=str, required=False,
        help='Ingress host or External IP. e.g. "127.0.0.1", "example.com"')
    kubernetes_model_parser.add_argument(
        'ingress_port', location='form', type=int, required=False,
        help='Ingress port or NodePort. e.g. "33000"')

    @kubernetes_api_namespace.marshal_with(kubernetes_model_params)
    def get(self, project_id: int, kubernetes_id: int):
        """get_kubernetes_id"""
        if api.dashboard_config.IS_ACTIVATE_AUTH:
            user_id = get_jwt_identity()
            role: ProjectUserRoleModel = db.session.query(ProjectUserRoleModel).filter(
                ProjectUserRoleModel.project_id == project_id,
                ProjectUserRoleModel.user_id == user_id).one_or_none()
            if role is None or role.project_role != ProjectRole.admin:
                raise ProjectUserRoleException("Invalid access.")
        return KubernetesModel.query.filter_by(kubernetes_id=kubernetes_id).one()

    @kubernetes_api_namespace.marshal_with(success_or_not)
    def put(self, project_id: int, kubernetes_id: int):
        """update_dbs_of_kubernetes_app"""
        kubernetes_model = KubernetesModel.query.filter_by(kubernetes_id=kubernetes_id).one()
        update_kubernetes_deployment_info(kubernetes_model)
        db.session.commit()
        db.session.close()
        response_body = {"status": True, "message": "Success."}
        return response_body

    @kubernetes_api_namespace.marshal_with(success_or_not)
    @kubernetes_api_namespace.expect(kubernetes_model_parser)
    def patch(self, project_id: int, kubernetes_id: int):
        """update_kubernetes_id"""
        args = self.kubernetes_model_parser.parse_args()
        config_path = "{0}.config".format(uuid.uuid4().hex)
        file = args['file']
        display_name = args['display_name']
        description = args['description']
        ingress_host = args['ingress_host']
        ingress_port = args['ingress_port']

        kubernetes_model: KubernetesModel = db.session.query(KubernetesModel).filter(
            KubernetesModel.kubernetes_id==kubernetes_id).one()
        prev_config_path = kubernetes_model.config_path
        is_update = False
        if display_name is not None:
            is_update = True
            kubernetes_model.display_name = display_name
        if description is not None:
            is_update = True
            kubernetes_model.description = description
        if ingress_host is not None:
            is_update = True
            kubernetes_model.ingress_host = ingress_host
        if ingress_port is not None:
            is_update = True
            kubernetes_model.ingress_port = ingress_port
        if file is not None:
            is_update = True
            kubernetes_model.config_path = config_path
            save_kubernetes_access_file(file, config_path)
            try:
                update_kubernetes_deployment_info(kubernetes_model)
                remove_kubernetes_access_file(prev_config_path)
            except Exception as error:
                remove_kubernetes_access_file(config_path)
                raise error
        if is_update:
            db.session.commit()
            db.session.close()
        return {"status": True, "message": "Success."}

    @kubernetes_api_namespace.marshal_with(success_or_not)
    def delete(self, project_id: int, kubernetes_id: int):
        """delete_kubernetes_id"""
        db.session.query(KubernetesModel).filter(KubernetesModel.kubernetes_id == kubernetes_id).delete()
        response_body = {"status": True, "message": "Success."}
        db.session.commit()
        db.session.close()
        return response_body
