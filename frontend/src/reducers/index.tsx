import {
  APIActions,
  APIRequestStartAction, APIRequestFailueAction, APIRequestSuccessAction,
  APIRequestActionCreators,
  uploadModelActionCreators,
  saveKubernetesHostActionCreators,
  addApplicationActionCreators,
  saveServiceActionCreators,
  fetchAllKubernetesHostsActionCreators,
  fetchAllApplicationsActionCreators,
  fetchApplicationByIdActionCreators,
  fetchAllModelsActionCreators,
  fetchAllServicesActionCreators,
  switchModelsActionCreators,
  fetchKubernetesHostByIdActionCreators,
  deleteKubernetesHostActionCreators,
  deleteKubernetesServicesActionCreators,
  syncKubernetesStatusActionCreators,
  fetchServiceByIdActionCreators,
  fetchServiceDescriptionsActionCreators
} from '@src/actions'
import { APIRequest, APIRequestStatusList} from '@src/apis/Core'
import { Application, Model, Service, SwitchModelParam, ModelResponse, KubernetesHost, FetchServicesParam, fetchServiceById } from '@src/apis'

export class AppState {
  constructor(
    // API states
    public uploadModel: APIRequest<ModelResponse> = { status: APIRequestStatusList.notStarted },
    public switchModels: APIRequest<boolean[]> = { status: APIRequestStatusList.notStarted },
    public saveKubernetesHost: APIRequest<boolean> = { status: APIRequestStatusList.notStarted },
    public addApplication: APIRequest<boolean> = { status: APIRequestStatusList.notStarted },
    public saveService: APIRequest<boolean> = { status: APIRequestStatusList.notStarted },
    public applications: APIRequest<Application[]> = { status: APIRequestStatusList.notStarted },
    public applicationById: APIRequest<Application> = { status: APIRequestStatusList.notStarted },
    public services: APIRequest<Service[]> = { status: APIRequestStatusList.notStarted },
    public serviceDescriptions: APIRequest<Service[]> = { status: APIRequestStatusList.notStarted },
    public serviceById: APIRequest<Service> = { status: APIRequestStatusList.notStarted },
    public models: APIRequest<Model[]> = { status: APIRequestStatusList.notStarted },
    public kubernetesHosts: APIRequest<KubernetesHost[]> = { status: APIRequestStatusList.notStarted },
    public kubernetesHostById: APIRequest<any> = { status: APIRequestStatusList.notStarted },
    public deleteKubernetesServices: APIRequest<boolean[]> = { status: APIRequestStatusList.notStarted },
    public syncKubernetesStatus: APIRequest<boolean> = { status: APIRequestStatusList.notStarted },
    // Notification status
    public notification = { toasts: [], id: -1 }
  ) { }
}

const initialState = new AppState()

function APIRequestReducerCreator<P = {}, S = {}, F = {}>(
  actionCreators: APIRequestActionCreators<P, S, F>,
  statePropertyName: string
) {
  function reducer(state: AppState = initialState, action: APIActions<P, S, F>) {
    const suffix: string = actionCreators.apiType
    const nextState: AppState = Object.assign({}, state)

    const isStarted = (item: any): item is APIRequestStartAction =>
      item.type === `${suffix}_REQUEST_START`
    const isFailed = (item: any): item is APIRequestFailueAction =>
      item.type === `${suffix}_FAILURE`
    const isSuccess = (item: any): item is APIRequestSuccessAction =>
      item.type === `${suffix}_SUCCESS`

    if (isStarted(action)) {
      nextState[statePropertyName] = { status: APIRequestStatusList.fetching }
    } else if (isFailed(action)) {
      nextState[statePropertyName] = { status: APIRequestStatusList.failue, error: action.error }
    } else if (isSuccess(action)) {
      nextState[statePropertyName] = { status: APIRequestStatusList.success, result: action.result }
    } else {
      return state
    }

    return nextState
  }
  return reducer
}

export const uploadModelReducer = APIRequestReducerCreator<{}, ModelResponse>(uploadModelActionCreators, 'uploadModel')
export const switchModelsReducer = APIRequestReducerCreator< SwitchModelParam[], boolean[] >(switchModelsActionCreators, 'switchModels')
export const addApplicationReducer = APIRequestReducerCreator<Application, boolean>(addApplicationActionCreators, 'addApplication')
export const saveServiceReducer = APIRequestReducerCreator<Application, boolean>(saveServiceActionCreators, 'saveService')
export const saveKubernetesHostReducer
  = APIRequestReducerCreator<KubernetesHost, boolean>(saveKubernetesHostActionCreators, 'saveKubernetesHost')
export const fetchAllKubernetesHostsReducer
  = APIRequestReducerCreator<{}, KubernetesHost[]>(fetchAllKubernetesHostsActionCreators, 'kubernetesHosts')
export const fetchAllApplicationsReducer = APIRequestReducerCreator<{}, Application[]>(fetchAllApplicationsActionCreators, 'applications')
export const fetchApplicationByIdReducer = APIRequestReducerCreator<{}, Application>(fetchApplicationByIdActionCreators, 'applicationById')
export const fetchKubernetesHostByIdReducer = APIRequestReducerCreator<{}, any>(fetchKubernetesHostByIdActionCreators, 'kubernetesHostById')
export const fetchAllModelsReducer = APIRequestReducerCreator<{}, Model[]>(fetchAllModelsActionCreators, 'models')
export const fetchAllServicesReducer = APIRequestReducerCreator<{}, Service[]>(fetchAllServicesActionCreators, 'services')
export const fetchServiceByIdReducer = APIRequestReducerCreator<FetchServicesParam, any>(fetchServiceByIdActionCreators, 'serviceById')
export const fetchServiceDescriptionsReducer
  = APIRequestReducerCreator<FetchServicesParam, any>(fetchServiceDescriptionsActionCreators, 'serviceDescriptions')
export const deleteKubernetesHostReducer
  = APIRequestReducerCreator<{id: number}, boolean>(deleteKubernetesHostActionCreators, 'deleteKubernetesHost')
export const deleteKubernetesServicesReducer
  = APIRequestReducerCreator<any, boolean[]>(deleteKubernetesServicesActionCreators, 'deleteKubernetesServices')
export const syncKubernetesStatusReducer
  = APIRequestReducerCreator<any, boolean[]>(syncKubernetesStatusActionCreators, 'syncKubernetesStatus')

/**
 * Notification with toasts
 *
 * @param state
 * @param action
 */
export function notificationReducer(state: AppState = initialState, action) {
  const { type } = action

  switch (type) {
    case 'NOTIFICATION_OPEN':
      const nextId = state.notification.id + 1
      const toastProp = {
        ...action.properties,
        id: nextId
      }
      const openNextNotification = {
        toasts: [toastProp].concat(state.notification.toasts),
        id: nextId
      }
      return {
        ...state,
        notification: openNextNotification
      }

    case 'NOTIFICATION_DISMISS':
      const dismissNextNotification = {
        ...state.notification,
        toasts: state.notification.toasts.filter(
          (toast) => toast.id !== action.id
        )
      }
      return {
        ...state,
        notification: dismissNextNotification
      }

    default:
      return state
  }
}
