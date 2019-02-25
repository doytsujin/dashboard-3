import json
import uuid

from datetime import datetime
from pathlib import Path

from . import api
from .common import kubernetes_cpu_to_float
from rekcurd_dashboard.models import db, DataServerModel, KubernetesModel, ApplicationModel, ServiceModel, ModelModel


def get_full_config_path(filename: str):
    """
    Get full path of Kubernetes config.
    :param filename:
    :return:
    """
    return f'{api.dashboard_config.DIR_KUBE_CONFIG}/{filename}'


def save_kubernetes_access_file(file, config_path):
    """
    Save Kubernetes config.
    :param file:
    :param config_path:
    :return:
    """
    full_config_path = get_full_config_path(config_path)
    file.save(full_config_path)
    return


def remove_kubernetes_access_file(config_path):
    """
    Remove Kubernetes config.
    :param config_path:
    :return:
    """
    full_config_path = get_full_config_path(config_path)
    Path(full_config_path).unlink()
    return


def update_kubernetes_deployment_info(kubernetes_model: KubernetesModel, target_applications: set = None):
    """
    Update Kubernetes deployment info.
    :param kubernetes_model:
    :param target_applications:
    :return:
    """
    full_config_path = get_full_config_path(kubernetes_model.config_path)
    from kubernetes import client, config
    config.load_kube_config(full_config_path)
    v1_api = client.AppsV1Api()
    list_deployment_for_all_namespaces = v1_api.list_deployment_for_all_namespaces(watch=False)

    """If target_applications is None, register all application from Kubernetes."""
    if target_applications is None:
        target_applications = set()
        for i in list_deployment_for_all_namespaces.items:
            labels = i.metadata.labels
            if labels is not None and labels.get("rekcurd-worker", "False") == "True":
                application_name = labels["app"]
                target_applications.add(application_name)

    """Application registration."""
    for application_name in target_applications:
        application_model = db.session.query(ApplicationModel).filter(
            ApplicationModel.application_name == application_name,
            ApplicationModel.project_id == KubernetesModel.project_id).one_or_none()
        if application_model is None:
            application_model = ApplicationModel(
                project_id=kubernetes_model.project_id,
                application_name=application_name)
            db.session.add(application_model)
            db.session.flush()

    """Service registration."""
    for i in list_deployment_for_all_namespaces.items:
        labels = i.metadata.labels
        if labels is None or labels.get("rekcurd-worker", "False") == "False":
            continue

        application_name = labels["app"]
        if application_name not in target_applications:
            continue

        service_id = labels["sel"]
        service_model: ServiceModel = db.session.query(ServiceModel).filter(
            ServiceModel.service_id == service_id).one_or_none()
        if service_model is None:
            service_level = i.metadata.namespace
            version = None
            filepath = None
            host = None
            port = None
            for env_ent in i.spec.template.spec.containers[0].env:
                if env_ent.name == "REKCURD_GRPC_PROTO_VERSION":
                    version = env_ent.value
                elif env_ent.name == "REKCURD_MODEL_FILE_PATH":
                    filepath = env_ent.value
                elif env_ent.name == "REKCURD_SERVICE_HOST":
                    host = env_ent.value
                elif env_ent.name == "REKCURD_SERVICE_PORT":
                    port = int(env_ent.value)

            """Model registration."""
            application_model: ApplicationModel = db.session.query(ApplicationModel).filter(
                ApplicationModel.application_name == application_name,
                ApplicationModel.project_id == KubernetesModel.project_id).one()
            model_model: ModelModel = db.session.query(ModelModel).filter(
                ModelModel.application_id == application_model.application_id,
                ModelModel.filepath == filepath).one_or_none()
            if model_model is None:
                model_model = ModelModel(application_id=application_model.application_id,
                                         filepath=filepath, description="Automatically registered.")
                db.session.add(model_model)
                db.session.flush()

            """Service registration."""
            service_model = ServiceModel(
                service_id=service_id,
                application_id=application_model.application_id,
                display_name="{}-{}".format(service_level, service_id),
                service_level=service_level,
                version=version,
                model_id=model_model.model_id,
                host=host,
                port=port)
            db.session.add(service_model)
            db.session.flush()
    return


def apply_rekcurd_to_kubernetes(
        project_id: int, application_id: int, service_level: str, version: str,
        service_host: str, service_port: int, replicas_default: int, replicas_minimum: int,
        replicas_maximum: int, autoscale_cpu_threshold: str, policy_max_surge: int,
        policy_max_unavailable: int, policy_wait_seconds: int, container_image: str,
        resource_request_cpu: str, resource_request_memory: str, resource_limit_cpu: str,
        resource_limit_memory: str, commit_message: str, service_model_assignment: int,
        service_git_url: str = "", service_git_branch: str = "", service_boot_script: str = "",
        service_id: str = None,
        **kwargs) -> str:
    """
    kubectl apply
    :param project_id:
    :param application_id:
    :param service_level:
    :param version:
    :param service_host:
    :param service_port:
    :param replicas_default:
    :param replicas_minimum:
    :param replicas_maximum:
    :param autoscale_cpu_threshold:
    :param policy_max_surge:
    :param policy_max_unavailable:
    :param policy_wait_seconds:
    :param container_image:
    :param resource_request_cpu:
    :param resource_request_memory:
    :param resource_limit_cpu:
    :param resource_limit_memory:
    :param commit_message:
    :param service_model_assignment:
    :param service_git_url:
    :param service_git_branch:
    :param service_boot_script:
    :param service_id:
    :param kwargs:
    :return:
    """
    __num_retry = 5
    progress_deadline_seconds = \
        int(__num_retry*policy_wait_seconds*replicas_maximum/(policy_max_surge+policy_max_unavailable))
    is_creation_mode = False
    if service_id is None:
        is_creation_mode = True
        service_id = uuid.uuid4().hex
    data_server_model: DataServerModel = db.session.query(DataServerModel).filter(
        DataServerModel.project_id == project_id).one()
    application_model: ApplicationModel = db.session.query(ApplicationModel).filter(
        ApplicationModel.application_id == application_id).one()
    application_name = application_model.application_name
    model_model: ModelModel = db.session.query(ModelModel).filter(
        ModelModel.model_id == service_model_assignment).one()

    for kubernetes_model in db.session.query(KubernetesModel).filter(KubernetesModel.project_id == project_id).all():
        full_config_path = get_full_config_path(kubernetes_model.config_path)
        from kubernetes import client, config
        config.load_kube_config(full_config_path)

        pod_env = [
            client.V1EnvVar(
                name="REKCURD_SERVICE_UPDATE_FLAG",
                value=commit_message
            ),
            client.V1EnvVar(
                name="REKCURD_DEBUG_MODE",
                value="False"
            ),
            client.V1EnvVar(
                name="REKCURD_APPLICATION_NAME",
                value=application_name
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_HOST",
                value=service_host
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_PORT",
                value=str(service_port)
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_ID",
                value=service_id
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_LEVEL",
                value=service_level
            ),
            client.V1EnvVar(
                name="REKCURD_GRPC_PROTO_VERSION",
                value=version
            ),
            client.V1EnvVar(
                name="REKCURD_MODEL_MODE",
                value=data_server_model.data_server_mode.value
            ),
            client.V1EnvVar(
                name="REKCURD_MODEL_FILE_PATH",
                value=model_model.filepath
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_GIT_URL",
                value=service_git_url
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_GIT_BRANCH",
                value=service_git_branch
            ),
            client.V1EnvVar(
                name="REKCURD_SERVICE_BOOT_SHELL",
                value=service_boot_script
            ),
        ]

        """Namespace registration."""
        core_vi = client.CoreV1Api()
        try:
            core_vi.read_namespace(name=service_level)
        except:
            api.logger.info("\"{}\" namespace created".format(service_level))
            v1_namespace = client.V1Namespace(
                api_version="v1",
                kind="Namespace",
                metadata=client.V1ObjectMeta(
                    name=service_level
                )
            )
            core_vi.create_namespace(
                body=v1_namespace
            )

        """Create/patch Deployment."""
        v1_deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name="{0}-deployment".format(service_id),
                namespace=service_level,
                labels={"rekcurd-worker": "True", "app": application_name, "sel": service_id}
            ),
            spec=client.V1DeploymentSpec(
                min_ready_seconds=policy_wait_seconds,
                progress_deadline_seconds=progress_deadline_seconds,
                replicas=replicas_default,
                revision_history_limit=3,
                selector=client.V1LabelSelector(
                    match_labels={"sel": service_id}
                ),
                strategy=client.V1DeploymentStrategy(
                    type="RollingUpdate",
                    rolling_update=client.V1RollingUpdateDeployment(
                        max_surge=policy_max_surge,
                        max_unavailable=policy_max_unavailable)
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"rekcurd-worker": "True", "app": application_name, "sel": service_id}
                    ),
                    spec=client.V1PodSpec(
                        affinity=client.V1Affinity(
                            pod_anti_affinity=client.V1PodAntiAffinity(
                                preferred_during_scheduling_ignored_during_execution=[
                                    client.V1WeightedPodAffinityTerm(
                                        pod_affinity_term=client.V1PodAffinityTerm(
                                            label_selector=client.V1LabelSelector(
                                                match_expressions=[
                                                    client.V1LabelSelectorRequirement(
                                                        key="app",
                                                        operator="In",
                                                        values=[service_id]
                                                    )
                                                ]
                                            ),
                                            topology_key="kubernetes.io/hostname"
                                        ),
                                        weight=100
                                    )
                                ]
                            )
                        ),
                        containers=[
                            client.V1Container(
                                env=pod_env,
                                image=container_image,
                                image_pull_policy="Always",
                                name=service_id,
                                ports=[
                                    client.V1ContainerPort(container_port=service_port)
                                ],
                                resources=client.V1ResourceRequirements(
                                    limits={
                                        "cpu": str(resource_limit_cpu),
                                        "memory": resource_limit_memory
                                    },
                                    requests={
                                        "cpu": str(resource_request_cpu),
                                        "memory": resource_request_memory
                                    }
                                ),
                                security_context=client.V1SecurityContext(
                                    privileged=True
                                )
                            )
                        ],
                        node_selector={"host": service_level}
                    )
                )
            )
        )
        apps_v1 = client.AppsV1Api()
        if is_creation_mode:
            api.logger.info("Deployment created.")
            apps_v1.create_namespaced_deployment(
                body=v1_deployment,
                namespace=service_level
            )
        else:
            api.logger.info("Deployment patched.")
            apps_v1.patch_namespaced_deployment(
                body=v1_deployment,
                name="{0}-deployment".format(service_id),
                namespace=service_level
            )

        """Create/patch Service."""
        v1_service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name="{0}-service".format(service_id),
                namespace=service_level,
                labels={"rekcurd-worker": "True", "app": application_name, "sel": service_id}
            ),
            spec=client.V1ServiceSpec(
                ports=[
                    client.V1ServicePort(
                        name="http2",
                        port=service_port,
                        protocol="TCP",
                        target_port=service_port
                    )
                ],
                selector={"sel": service_id},
                type="NodePort"
            )
        )
        core_vi = client.CoreV1Api()
        if is_creation_mode:
            api.logger.info("Service created.")
            core_vi.create_namespaced_service(
                namespace=service_level,
                body=v1_service
            )
        else:
            api.logger.info("Service patched.")
            core_vi.patch_namespaced_service(
                namespace=service_level,
                name="{0}-service".format(service_id),
                body=v1_service
            )

        """Create/patch Autoscaler."""
        v1_horizontal_pod_autoscaler = client.V1HorizontalPodAutoscaler(
            api_version="autoscaling/v1",
            kind="HorizontalPodAutoscaler",
            metadata=client.V1ObjectMeta(
                name="{0}-autoscaling".format(service_id),
                namespace=service_level,
                labels={"rekcurd-worker": "True", "app": application_name, "sel": service_id}
            ),
            spec=client.V1HorizontalPodAutoscalerSpec(
                max_replicas=replicas_maximum,
                min_replicas=replicas_minimum,
                scale_target_ref=client.V1CrossVersionObjectReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name="{0}-deployment".format(service_id)
                ),
                target_cpu_utilization_percentage=autoscale_cpu_threshold
            )
        )
        autoscaling_v1 = client.AutoscalingV1Api()
        if is_creation_mode:
            api.logger.info("Autoscaler created.")
            autoscaling_v1.create_namespaced_horizontal_pod_autoscaler(
                namespace=service_level,
                body=v1_horizontal_pod_autoscaler
            )
        else:
            api.logger.info("Autoscaler patched.")
            autoscaling_v1.patch_namespaced_horizontal_pod_autoscaler(
                namespace=service_level,
                name="{0}-autoscaling".format(service_id),
                body=v1_horizontal_pod_autoscaler
            )

        """Create/patch istio."""
        # TODO: Implement here.
        custom_object_api = client.CustomObjectsApi()
        if is_creation_mode:
            api.logger.info("Istio created.")
            custom_object_api.create_namespaced_custom_object(
                group="",
                version="",
                namespace=service_level,
                plural="",
                body=None
            )
        else:
            api.logger.info("Istio patched.")
            custom_object_api.patch_namespaced_custom_object(
                group="",
                version="",
                namespace=service_level,
                plural="",
                name="",
                body=None
            )

        """Register service."""
        display_name = "{0}-{1}".format(service_level, service_id)
        if is_creation_mode:
            service_model = ServiceModel(
                service_id=service_id, application_id=application_id, display_name=display_name,
                description=commit_message, service_level=service_level, version=version,
                model_id=service_model_assignment, host=service_host, port=service_port)
            db.session.add(service_model)
            db.session.flush()

        """Finish."""
        return service_id


def delete_kubernetes_deployment(kubernetes_models: list, service_id: str):
    """
    Delete Kubernetes deployment.
    :param kubernetes_models:
    :param service_id:
    :return:
    """
    service_model: ServiceModel = db.session.query(ServiceModel).filter(ServiceModel.service_id == service_id).one()
    for kubernetes_model in kubernetes_models:
        full_config_path = get_full_config_path(kubernetes_model.config_path)
        from kubernetes import client, config
        config.load_kube_config(full_config_path)
        """Deployment"""
        apps_v1 = client.AppsV1Api()
        apps_v1.delete_namespaced_deployment(
            name="{0}-deployment".format(service_id),
            namespace=service_model.service_level,
            body=client.V1DeleteOptions()
        )
        """Service"""
        core_vi = client.CoreV1Api()
        core_vi.delete_namespaced_service(
            name="{0}-service".format(service_id),
            namespace=service_model.service_level,
            body=client.V1DeleteOptions()
        )
        """Autoscaler"""
        autoscaling_v1 = client.AutoscalingV1Api()
        autoscaling_v1.delete_namespaced_horizontal_pod_autoscaler(
            name="{0}-autoscaling".format(service_id),
            namespace=service_model.service_level,
            body=client.V1DeleteOptions()
        )
        """Istio"""
        # TODO: Implement
        custom_object_api = client.CustomObjectsApi()
    db.session.query(ServiceModel).filter(ServiceModel.service_id == service_id).delete()
    db.session.flush()
    return


def load_kubernetes_deployment_info(project_id: int, application_id: int, service_id: str) -> dict:
    """
    Load deployment info from Kubernetes.
    :param project_id:
    :param application_id:
    :param service_id:
    :return:
    """
    kubernetes_model: KubernetesModel = db.session.query(KubernetesModel).filter(
        KubernetesModel.project_id == project_id).first()
    service_model: ServiceModel = db.session.query(ServiceModel).filter(
        ServiceModel.service_id == service_id).one()

    full_config_path = get_full_config_path(kubernetes_model.config_path)
    from kubernetes import client, config
    config.load_kube_config(full_config_path)

    apps_v1 = client.AppsV1Api()
    v1_deployment = apps_v1.read_namespaced_deployment(
        name="{0}-deployment".format(service_id),
        namespace=service_model.service_level
    )
    autoscaling_v1 = client.AutoscalingV1Api()
    v1_horizontal_pod_autoscaler = autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(
        name="{0}-autoscaling".format(service_id),
        namespace=service_model.service_level
    )

    deployment_info = {}
    filepath = None
    deployment_info["application_name"] = v1_deployment.metadata.labels["app"]
    deployment_info["service_id"] = service_id
    for env_ent in v1_deployment.spec.template.spec.containers[0].env:
        if env_ent.name == "REKCURD_SERVICE_UPDATE_FLAG":
            deployment_info["commit_message"] = env_ent.value
        elif env_ent.name == "REKCURD_SERVICE_HOST":
            deployment_info["service_host"] = env_ent.value
        elif env_ent.name == "REKCURD_SERVICE_PORT":
            deployment_info["service_port"] = int(env_ent.value)
        elif env_ent.name == "REKCURD_SERVICE_LEVEL":
            deployment_info["service_level"] = env_ent.value
        elif env_ent.name == "REKCURD_GRPC_PROTO_VERSION":
            deployment_info["version"] = env_ent.value
        elif env_ent.name == "REKCURD_MODEL_FILE_PATH":
            filepath = env_ent.value
        elif env_ent.name == "REKCURD_SERVICE_GIT_URL":
            deployment_info["service_git_url"] = env_ent.value
        elif env_ent.name == "REKCURD_SERVICE_GIT_BRANCH":
            deployment_info["service_git_branch"] = env_ent.value
        elif env_ent.name == "REKCURD_SERVICE_BOOT_SHELL":
            deployment_info["service_boot_script"] = env_ent.value
    model_model: ModelModel = db.session.query(ModelModel).filter(
        ModelModel.application_id == application_id, ModelModel.filepath == filepath).one()
    deployment_info["service_model_assignment"] = model_model.model_id
    deployment_info["replicas_default"] = v1_deployment.spec.replicas
    deployment_info["replicas_minimum"] = v1_horizontal_pod_autoscaler.spec.min_replicas
    deployment_info["replicas_maximum"] = v1_horizontal_pod_autoscaler.spec.max_replicas
    deployment_info["autoscale_cpu_threshold"] = v1_horizontal_pod_autoscaler.spec.target_cpu_utilization_percentage
    deployment_info["policy_max_surge"] = v1_deployment.spec.strategy.rolling_update.max_surge
    deployment_info["policy_max_unavailable"] = v1_deployment.spec.strategy.rolling_update.max_unavailable
    deployment_info["policy_wait_seconds"] = v1_deployment.spec.min_ready_seconds
    deployment_info["container_image"] = v1_deployment.spec.template.spec.containers[0].image
    deployment_info["resource_request_cpu"] = \
        kubernetes_cpu_to_float(v1_deployment.spec.template.spec.containers[0].resources.requests["cpu"])
    deployment_info["resource_request_memory"] = \
        v1_deployment.spec.template.spec.containers[0].resources.requests["memory"]
    deployment_info["resource_limit_cpu"] = \
        kubernetes_cpu_to_float(v1_deployment.spec.template.spec.containers[0].resources.limits["cpu"])
    deployment_info["resource_limit_memory"] = \
        v1_deployment.spec.template.spec.containers[0].resources.limits["memory"]
    return deployment_info


def switch_model_assignment(project_id: int, application_id: int, service_id: str, model_id: int):
    """
    Switch model assignment.
    :param project_id:
    :param application_id:
    :param service_id:
    :param model_id:
    :return:
    """
    service_model: ServiceModel = db.session.query(ServiceModel).filter(
        ServiceModel.service_id == service_id).one()
    deployment_info = load_kubernetes_deployment_info(project_id, application_id, service_id)
    deployment_info["service_model_assignment"] = model_id
    deployment_info["commit_message"] = "model_id={0} on {1:%Y%m%d%H%M%S}".format(model_id, datetime.utcnow())

    apply_rekcurd_to_kubernetes(
        project_id=project_id, application_id=application_id, service_id=service_id, **deployment_info)

    service_model.model_id = model_id
    db.session.flush()
    return


def backup_kubernetes_deployment(
        kubernetes_model: KubernetesModel, application_model: ApplicationModel, service_model: ServiceModel):
    """
    Backup Kubernetes deployment.
    :param kubernetes_model:
    :param application_model:
    :param service_model:
    :return:
    """
    full_config_path = get_full_config_path(kubernetes_model.config_path)
    from kubernetes import client, config
    config.load_kube_config(full_config_path)
    save_dir = Path(api.dashboard_config.DIR_KUBE_CONFIG, application_model.application_name)
    save_dir.mkdir(parents=True, exist_ok=True)
    api_client = client.ApiClient()

    """Deployment"""
    apps_v1 = client.AppsV1Api()
    v1_deployment = apps_v1.read_namespaced_deployment(
        name="{0}-deployment".format(service_model.service_id),
        namespace=service_model.service_level,
        exact=True,
        export=True
    )
    json.dump(api_client.sanitize_for_serialization(v1_deployment),
              Path(save_dir, "{0}-deployment.json".format(service_model.service_id)).open("w", encoding='utf-8'),
              ensure_ascii=False, indent=2)
    """Service"""
    core_vi = client.CoreV1Api()
    v1_service = core_vi.read_namespaced_service(
        name="{0}-service".format(service_model.service_id),
        namespace=service_model.service_level,
        exact=True,
        export=True
    )
    json.dump(api_client.sanitize_for_serialization(v1_service),
              Path(save_dir, "{0}-service.json".format(service_model.service_id)).open("w", encoding='utf-8'),
              ensure_ascii=False, indent=2)
    """Autoscaler"""
    autoscaling_v1 = client.AutoscalingV1Api()
    v1_horizontal_pod_autoscaler = autoscaling_v1.read_namespaced_horizontal_pod_autoscaler(
        name="{0}-autoscaling".format(service_model.service_id),
        namespace=service_model.service_level,
        exact=True,
        export=True
    )
    json.dump(api_client.sanitize_for_serialization(v1_horizontal_pod_autoscaler),
              Path(save_dir, "{0}-autoscaling.json".format(service_model.service_id)).open("w", encoding='utf-8'),
              ensure_ascii=False, indent=2)
    """Istio"""
    # TODO: Implement
    custom_object_api = client.CustomObjectsApi()
    return
