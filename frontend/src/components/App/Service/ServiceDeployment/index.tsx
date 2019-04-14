import * as React from 'react'
import { connect } from 'react-redux'
import { withRouter, RouteComponentProps } from 'react-router-dom'
import { Alert, Card, CardBody, Button } from 'reactstrap'
import { Formik, Form } from 'formik'
import * as Yup from "yup";

import { APIRequest, isAPISucceeded, isAPIFailed } from '@src/apis/Core'
import {
  Service, Model, FetchServiceByIdParam,
  FetchModelByIdParam, ServiceDeploymentParam, UpdateServiceParam
} from '@src/apis'
import {
  fetchServiceByIdDispatcher,
  fetchAllModelsDispatcher,
  saveServiceDeploymentDispatcher,
  updateServiceDispatcher,
  addNotification
} from '@src/actions'
import { APIRequestResultsRenderer } from '@common/APIRequestResultsRenderer'
import * as ServiceDeploymentForm from './ServiceDeploymentForm'
import * as SingleServiceForm from './SingleServiceForm'


/**
 * Page for adding service
 * You can create service ONLY when your application is deployed with Kubernetes.
 */
class ServiceDeployment extends React.Component<SaveServiceProps, SaveServiceState> {
  constructor(props, context) {
    super(props, context)

    this.renderForm = this.renderForm.bind(this)
    this.onServiceInfoSubmit = this.onServiceInfoSubmit.bind(this)
    this.onDeploymentSubmit = this.onDeploymentSubmit.bind(this)
    this.onCancel = this.onCancel.bind(this)
    this.state = {
      submitting: false,
      notified: false,
    }
  }

  componentDidMount(): void {
    this.props.fetchAllModels(this.props.match.params)
    if (this.props.method === 'patch') {
      this.props.fetchServiceById({
        isKubernetes: this.props.kubernetesMode,
        isOnlyDescription: false,
        serviceId: this.props.match.params.serviceId,
        ...this.props.match.params
      })
    }
  }

  static getDerivedStateFromProps(nextProps: SaveServiceProps, prevState: SaveServiceState){
    const { saveServiceDeploymentStatus } = nextProps
    const { push } = nextProps.history
    const { projectId, applicationId } = nextProps.match.params
    const { submitting, notified } = prevState

    // Close modal when API successfully finished
    if (submitting && !notified) {
      const succeeded: boolean = isAPISucceeded<boolean>(saveServiceDeploymentStatus) && saveServiceDeploymentStatus.result
      const failed: boolean = (isAPISucceeded<boolean>(saveServiceDeploymentStatus) && !saveServiceDeploymentStatus.result) || isAPIFailed<boolean>(saveServiceDeploymentStatus)
      if (succeeded) {
        nextProps.addNotification({ color: 'success', message: 'Successfully saved service' })
        push(`/projects/${projectId}/applications/${applicationId}`)
        return { submitting: false, notified: true }
      } else if (failed) {
        nextProps.addNotification({ color: 'error', message: 'Something went wrong. Try again later' })
        return { submitting: false, notified: true }
      }
    }
    return null
  }

  render() {
    const { method, kubernetesMode, fetchServiceByIdStatus, fetchAllModelsStatus } = this.props
    const targetStatus = (method === 'patch') ?
      {service: fetchServiceByIdStatus, models: fetchAllModelsStatus} :
      {models: fetchAllModelsStatus}

    return(
      <APIRequestResultsRenderer
        render={this.renderForm}
        APIStatus={targetStatus}
      />
    )
  }

  renderForm(params) {
    const { kubernetesMode, method } = this.props

    let ValidationSchema
    let InitialValues
    let onSubmit
    let formContent
    if (kubernetesMode) {
      ValidationSchema = Yup.object().shape({
        ...SingleServiceForm.SingleServiceSchema,
        ...ServiceDeploymentForm.ServiceDeploymentSchema
      })
      onSubmit = this.onDeploymentSubmit
      formContent = (
        <React.Fragment>
          <SingleServiceForm.SingleServiceForm isPost={(method === 'post')} models={params.models} />
          <ServiceDeploymentForm.ServiceDeploymentForm isPost={(method === 'post')} />
        </React.Fragment>
      )
      if (method === 'post') {
        InitialValues = {
          ...SingleServiceForm.SingleServiceDefaultInitialValues,
          ...ServiceDeploymentForm.ServiceDeploymentDefaultInitialValues
        }
      } else {
        InitialValues = {
          serviceModelAssignment: params.service.modelId,
          ...params.service
        }
      }
    } else {
      ValidationSchema = Yup.object().shape({
        ...SingleServiceForm.SingleServiceSchema
      })
      formContent = (
        <React.Fragment>
          <SingleServiceForm.SingleServiceForm isPost={(method === 'post')} models={params.models} />
        </React.Fragment>
      )
      if (method === 'post') {
        InitialValues = {
          ...SingleServiceForm.SingleServiceDefaultInitialValues
        }
        onSubmit = this.onDeploymentSubmit
      } else {
        InitialValues = {
          serviceModelAssignment: params.service.modelId,
          ...params.service
        }
        onSubmit = this.onServiceInfoSubmit
      }
    }
    const FormikContents = (
      <Formik
        initialValues={InitialValues}
        validationSchema={ValidationSchema}
        onSubmit={onSubmit}
        onReset={this.onCancel}>
        {({ isSubmitting }) => (
          <Form>
            {formContent}
            {this.renderButtons(isSubmitting)}
          </Form>
        )}
      </Formik>
    )

    return (
      <React.Fragment>
        { FormikContents }
      </React.Fragment>
    )
  }

  /**
   * Render control buttons
   *
   * Put on footer of this modal
   */
  renderButtons(isSubmitting): JSX.Element {
    const { method, kubernetesMode } = this.props

    if (isSubmitting) {
      return (
        <Card className='mb-3'>
          <CardBody>
            <div className='loader loader-primary loader-xs mr-2' />
            Submitting...
          </CardBody>
        </Card>
      )
    }

    return (
      <Card className='mb-3'>
        <CardBody className='text-right'>
          <Button color='success' type='submit'>
            <i className='fas fa-check fa-fw mr-2'></i>
            {method === 'post' ? 'Add Service' : kubernetesMode ? 'Rolling-update Service' : 'Update Service description'}
          </Button>
          {' '}
          <Button outline color='info' type='reset'>
            <i className='fas fa-ban fa-fw mr-2'></i>
            Reset
          </Button>
        </CardBody>
      </Card>
    )
  }

  /**
   * Handle cancel button
   *
   * Reset form and move to application list page
   */
  onCancel() {
    const { push } = this.props.history
    const { projectId, applicationId } = this.props.match.params
    push(`/projects/${projectId}/applications/${applicationId}`)
  }

  onServiceInfoSubmit(parameters) {
    const { updateServiceDeployment, method } = this.props
    const { projectId, applicationId, serviceId } = this.props.match.params

    const request: UpdateServiceParam = {
      projectId,
      applicationId,
      serviceId,
      method,
      ...parameters
    }

    this.setState({ submitting: true, notified: false })
    return updateServiceDeployment(request)
  }

  onDeploymentSubmit(parameters) {
    const { saveServiceDeployment, kubernetesMode, method } = this.props
    const { projectId, applicationId } = this.props.match.params

    const request: ServiceDeploymentParam = {
      projectId,
      applicationId,
      isKubernetes: kubernetesMode,
      method,
      ...parameters
    }

    this.setState({ submitting: true, notified: false })
    return saveServiceDeployment(request)
  }
}

type SaveServiceProps =
  StateProps & DispatchProps
  & RouteComponentProps<{projectId: number, applicationId: string, serviceId?: string}>
  & CustomProps

interface SaveServiceState {
  submitting: boolean
  notified: boolean
}

interface CustomProps {
  method: string
  kubernetesMode: boolean
}

interface StateProps {
  fetchServiceByIdStatus: APIRequest<Service>
  fetchAllModelsStatus: APIRequest<Model[]>
  saveServiceDeploymentStatus: APIRequest<boolean>
  updateServiceStatus: APIRequest<boolean>
}

const mapStateToProps = (state: any, extraProps: CustomProps) => (
  {
    fetchServiceByIdStatus: state.fetchServiceByIdReducer.fetchServiceById,
    fetchAllModelsStatus: state.fetchAllModelsReducer.fetchAllModels,
    saveServiceDeploymentStatus: state.saveServiceDeploymentReducer.saveServiceDeployment,
    updateServiceStatus: state.updateServiceReducer.updateService,
    ...state.form,
    ...extraProps
  }
)

export interface DispatchProps {
  fetchServiceById: (params: FetchServiceByIdParam) => Promise<void>
  fetchAllModels: (params: FetchModelByIdParam) => Promise<void>
  saveServiceDeployment: (params: ServiceDeploymentParam) => Promise<void>
  updateServiceDeployment: (params: UpdateServiceParam) => Promise<void>
  addNotification: (params) => Promise<void>
}

const mapDispatchToProps = (dispatch): DispatchProps => {
  return {
    fetchServiceById: (params: FetchServiceByIdParam) => fetchServiceByIdDispatcher(dispatch, params),
    fetchAllModels: (params: FetchModelByIdParam) => fetchAllModelsDispatcher(dispatch, params),
    saveServiceDeployment: (params: ServiceDeploymentParam) => saveServiceDeploymentDispatcher(dispatch, params),
    updateServiceDeployment: (params: UpdateServiceParam) => updateServiceDispatcher(dispatch, params),
    addNotification: (params) => dispatch(addNotification(params))
  }
}

export default withRouter(
  connect<StateProps, DispatchProps, CustomProps & RouteComponentProps<{projectId: number, applicationId: string, serviceId?: string}> & CustomProps>(
    mapStateToProps, mapDispatchToProps
  )(ServiceDeployment)
)
