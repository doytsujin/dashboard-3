import * as React from 'react'
import { connect } from 'react-redux'
import { Card, CardBody, Button, CardTitle, UncontrolledTooltip } from 'reactstrap'
import { dataServerMode } from '@components/Common/Enum'

import * as Yup from "yup";
import { Field, Form, Formik } from "formik";

import { FormikInput } from '@common/Field'


const DataServerSchema = Yup.object().shape({
  dataServerMode: Yup.string()
    .oneOf([dataServerMode.local.toString(), dataServerMode.ceph_s3.toString(), dataServerMode.aws_s3.toString()])
    .required('Required'),
  cephAccessKey: Yup.string()
    .max(128),
  cephSecretKey: Yup.string()
    .max(128),
  cephHost: Yup.string()
    .max(512),
  cephPort: Yup.number()
    .positive()
    .integer(),
  cephIsSecure: Yup.bool(),
  cephBucketName: Yup.string()
    .max(128),
  awsAccessKey: Yup.string()
    .max(128),
  awsSecretKey: Yup.string()
    .max(128),
  awsBucketName: Yup.string()
    .max(128)
});

class DataServerFormImpl extends React.Component<DataServerFormProps, DataServerState> {
  constructor(props, context) {
    super(props, context)
    this.state = {
      dataServerMode: this.props.initialValues.dataServerMode
    }

    this.onChange = this.onChange.bind(this)
  }

  onChange(event) {
    if (this.state.dataServerMode !== event.target.value) {
      this.setState({dataServerMode: event.target.value})
    }
  }

  private renderModes() {
    const modes = Object.values(dataServerMode).map((modeName: string) => {
      return {
        value: modeName,
        label: modeName
      }
    })
    return (
      <Field
        name="dataServerMode"
        label="Data Server Mode"
        component={FormikInput}
        type="select"
        className='form-control'
        placeholder="Select your data server. For production, selecting online storage is recommended."
        options={modes}
        onChange={this.onChange}
        required />
    )
  }

  render() {
    const { onSubmit, onCancel, method } = this.props
    const initialValues = {
      ...this.props.initialValues
    }
    let fields = null
    if (this.state.dataServerMode === dataServerMode.ceph_s3.toString()) {
      const yesno = [{value: true, label: "Yes"}, {value: false, label: "No"}]
      fields = (
        <Card className='mb-3'>
          <CardBody>
            <Field
              name="cephAccessKey"
              label="Ceph Access Key"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
            <Field
              name="cephSecretKey"
              label="Ceph Secret Key"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
            <Field
              name="cephHost"
              label="Ceph Host URL"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. '127.0.0.1'"
              required />
            <Field
              name="cephPort"
              label="Ceph Port"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. '80'"
              required />
            <Field
              name="cephIsSecure"
              label="Does Ceph use SSL?"
              component={FormikInput}
              type="select"
              className="form-control"
              placeholder="If ceph is secure, then choose 'Yes'."
              options={yesno}
              onChange={()=>{}}
              required />
            <Field
              name="cephBucketName"
              label="Ceph Bucket Name"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
          </CardBody>
        </Card>
      )
    } else if (this.state.dataServerMode === dataServerMode.aws_s3.toString()) {
      fields = (
        <Card className='mb-3'>
          <CardBody>
            <Field
              name="awsAccessKey"
              label="AWS Access Key"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
            <Field
              name="awsSecretKey"
              label="AWS Secret Key"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
            <Field
              name="awsBucketName"
              label="AWS Bucket Name"
              component={FormikInput}
              className="form-control"
              placeholder="e.g. 'xxxxx'"
              required />
          </CardBody>
        </Card>
      )
    } else {
      fields = null
    }

    return (
      <div className='pt-3 pr-3 pl-3'>
        <h1>
          <i className='fas fa-plug fa-fw mr-2'></i>
          {method === 'post' ? 'Add' : 'Edit'} DataServer
        </h1>
        <Formik
          initialValues={initialValues}
          validationSchema={DataServerSchema}
          onSubmit={onSubmit}
          onReset={onCancel}>
          {({ errors, touched, isSubmitting }) => (
            <Form>
              <Card className='mb-3'>
                <CardBody>
                  {this.renderModes()}
                </CardBody>
              </Card>
              {fields}
              <Card>
                <CardBody className='text-right'>
                  <Button color='success' type='submit' disabled={isSubmitting} >
                    <i className='fas fa-check fa-fw mr-2'></i>
                    {method === 'post' ? 'Submit' : 'Update'}
                  </Button>
                  {' '}
                  <Button outline color='info' type='reset'>
                    <i className='fas fa-ban fa-fw mr-2'></i>
                    Cancel
                  </Button>
                </CardBody>
              </Card>
            </Form>
          )}
        </Formik>
      </div>
    )
  }
}

type DataServerFormProps = CustomProps

interface DataServerState {
  dataServerMode: string
}

const defaultInitialValues = {
  dataServerMode: '',
  cephAccessKey: '',
  cephSecretKey: '',
  cephHost: '',
  cephPort: 7300,
  cephIsSecure: false,
  cephBucketName: '',
  awsAccessKey: '',
  awsSecretKey: '',
  awsBucketName: '',
}

export interface CustomProps {
  onCancel
  onSubmit
  method: string
  initialValues?: {
    dataServerMode: string
    cephAccessKey: string
    cephSecretKey: string
    cephHost: string
    cephPort: number
    cephIsSecure: boolean
    cephBucketName: string
    awsAccessKey: string
    awsSecretKey: string
    awsBucketName: string
  }
}

export const DataServerForm = connect(
  (state: any, extraProps: CustomProps) => ({
    ...state.form,
    initialValues: {
      ...defaultInitialValues,
      ...extraProps.initialValues
    },
  })
)(DataServerFormImpl)
