import * as React from 'react'
import { connect } from 'react-redux'
import { Dispatch } from 'redux'
import { withRouter, RouteComponentProps } from 'react-router'
import { Table, Row, Col, Button } from 'reactstrap'

import { AccessControlList, Application, UserInfo, UserRole } from '@src/apis'
import { APIRequest } from '@src/apis/Core'
import { fetchAccessControlListDispatcher, fetchApplicationByIdDispatcher } from '@src/actions'
import { APIRequestResultsRenderer } from '@common/APIRequestResultsRenderer'
import AddUserModal from './AddUserModal'

interface StateProps {
  accessControlList: APIRequest<AccessControlList>
  application: APIRequest<Application>
  userInfoStatus: APIRequest<UserInfo>,
}
interface DispatchProps {
  fetchAccessControlList: (applicationId: string) => Promise<void>
  fetchApplicationById: (id: string) => Promise<void>
}
type AdminProps = StateProps & DispatchProps & RouteComponentProps<{applicationId: string}>

interface AdminState {
  isAddUserModalOpen: boolean
}

class Admin extends React.Component<AdminProps, AdminState> {
  constructor(props: AdminProps) {
    super(props)
    this.renderAccessControlList = this.renderAccessControlList.bind(this)
    this.toggleAddUserModalOpen = this.toggleAddUserModalOpen.bind(this)
    this.state = {
      isAddUserModalOpen: false
    }
  }
  componentWillMount() {
    const { fetchAccessControlList, fetchApplicationById, match } = this.props
    fetchAccessControlList(match.params.applicationId)
    fetchApplicationById(match.params.applicationId)
  }
  render() {
    const { accessControlList, application, userInfoStatus } = this.props
    return (
      <APIRequestResultsRenderer
        APIStatus={{ accessControlList, application, userInfoStatus }}
        render={this.renderAccessControlList}
      />
    )
  }
  renderAccessControlList(results) {
    const { applicationId } = this.props.match.params
    const application: Application = results.application
    const acl: AccessControlList[] = results.accessControlList
    const userInfo: UserInfo = results.userInfoStatus
    const isAdmin: boolean = userInfo.roles.some((role: UserRole) => {
      return applicationId === String(role.applicationId) && role.role === 'admin'
    })
    return this.renderContent(application.name, acl, isAdmin)
  }
  renderContent(applicationName: string, acl: AccessControlList[], isAdmin: boolean) {
    const { isAddUserModalOpen } = this.state
    const tableBody = acl.map((e: AccessControlList, i: number) => {
      return (
        <tr key={i}>
          <td>{e.userUid}</td>
          <td>{e.userName}</td>
          <td>{e.role.replace(/Role./, '')}</td>
        </tr>
      )
    })
    let addUserButton
    if (isAdmin) {
      addUserButton = (
        <Col xs='5' className='text-right'>
          <Button
            color='primary'
            size='sm'
            onClick={this.toggleAddUserModalOpen}
          >
            <i className='fas fa-user-plus fa-fw mr-2'></i>
            Add User
          </Button>
        </Col>
      )
    }
    return (
      <div className='pb-5'>
        <Row className='align-items-center mb-5'>
          <Col xs='7'>
            <h1>
              <i className='fas fa-ship fa-fw mr-2'></i>
              {applicationName}
            </h1>
          </Col>
          {addUserButton}
        </Row>
        <AddUserModal
          isModalOpen={isAddUserModalOpen}
          toggle={this.toggleAddUserModalOpen}
        />
        <h3>
          <i className='fas fa-unlock fa-fw mr-2'></i>
          Access Control List
        </h3>
        <hr />
        <Table hover className='mb-3'>
          <thead>
            <tr className='bg-light text-primary'>
              <th>ID</th><th>Name</th><th>Role</th>
            </tr>
          </thead>
          <tbody>{tableBody}</tbody>
        </Table>
      </div>
    )
  }
  private toggleAddUserModalOpen() {
    const { isAddUserModalOpen } = this.state
    this.setState({
      isAddUserModalOpen: !isAddUserModalOpen,
    })
  }
}

export default withRouter(
  connect(
    (state: any): StateProps => {
      return {
        accessControlList: state.fetchAccessControlListReducer.accessControlList,
        application: state.fetchApplicationByIdReducer.applicationById,
        userInfoStatus: state.userInfoReducer.userInfo,
      }
    },
    (dispatch: Dispatch): DispatchProps => {
      return {
        fetchAccessControlList: (applicationId: string) => fetchAccessControlListDispatcher(dispatch, { applicationId }),
        fetchApplicationById: (id: string) => fetchApplicationByIdDispatcher(dispatch, { id }),
      }
    }
  )(Admin))
