package ru.ispras.lingvodoc.frontend.app.services

import com.greencatsoft.angularjs.core._
import com.greencatsoft.angularjs.{AngularExecutionContextProvider, Runnable, injectable}

import scala.scalajs.js
import scala.util.{Failure, Success}


@js.native
@injectable("$route")
trait RouteStatus extends js.Object {
  val current: Route = js.native
}

class AppInitializer(rootScope: RootScope,
                     route: RouteStatus,
                     backend: BackendService,
                     userService: UserService,
                     val timeout: Timeout,
                     val exceptionHandler: ExceptionHandler)
  extends Runnable
    with AngularExecutionContextProvider {

  import org.scalajs.dom._

  // update page title
  rootScope.$on("$routeChangeSuccess", () => {
    route.current.title foreach (title => document.title = title)
    rootScope.$broadcast("route.changeSuccess")
  })

  rootScope.$on("$routeChangeStart", () => {
    rootScope.$broadcast("route.changeStart")
  })


  rootScope.$on("$locationChangeStart", () => {
    backend.getCurrentUser onComplete {
      case Success(user) =>
        userService.setUser(user)
      case Failure(e) =>
        userService.removeUser()
    }
  })

  // user logged in
  rootScope.$on("user.login", () => {
    backend.getCurrentUser foreach { user =>
      userService.setUser(user)
    }
  })

  // user logged out
  rootScope.$on("user.logout", () => {
    userService.removeUser()
  })
}
