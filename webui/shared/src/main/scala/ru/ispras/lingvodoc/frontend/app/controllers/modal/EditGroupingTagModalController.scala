package ru.ispras.lingvodoc.frontend.app.controllers.modal

import com.greencatsoft.angularjs.core.{ExceptionHandler, Scope, Timeout}
import com.greencatsoft.angularjs.extensions.{ModalInstance, ModalOptions, ModalService}
import com.greencatsoft.angularjs.{AngularExecutionContextProvider, injectable}
import ru.ispras.lingvodoc.frontend.app.controllers.base.BaseModalController
import ru.ispras.lingvodoc.frontend.app.controllers.common.{DictionaryTable, Value}
import ru.ispras.lingvodoc.frontend.app.controllers.traits.SimplePlay
import ru.ispras.lingvodoc.frontend.app.model._
import ru.ispras.lingvodoc.frontend.app.services.BackendService

import scala.concurrent.Future
import scala.scalajs.js
import scala.scalajs.js.JSConverters._
import scala.scalajs.js.UndefOr
import scala.scalajs.js.annotation.JSExport

@js.native
trait EditGroupingTagScope extends Scope {
  var pageLoaded: Boolean = js.native
  var dictionaryTable: DictionaryTable = js.native
  var searchQuery: String = js.native
  var searchResults: js.Array[DictionaryTable] = js.native
  var size: Int = js.native
  var pageNumber: Int = js.native
  var resultEntriesCount: Int = js.native

}

@injectable("EditGroupingTagModalController")
class EditGroupingTagModalController(scope: EditGroupingTagScope,
                                     modal: ModalService,
                                     instance: ModalInstance[Unit],
                                     backend: BackendService,
                                     timeout: Timeout,
                                     val exceptionHandler: ExceptionHandler,
                                     params: js.Dictionary[js.Function0[js.Any]])
  extends BaseModalController(scope, modal, instance, timeout, params)
    with AngularExecutionContextProvider
    with SimplePlay {

  private[this] val dictionaryClientId = params("dictionaryClientId").asInstanceOf[Int]
  private[this] val dictionaryObjectId = params("dictionaryObjectId").asInstanceOf[Int]
  private[this] val perspectiveClientId = params("perspectiveClientId").asInstanceOf[Int]
  private[this] val perspectiveObjectId = params("perspectiveObjectId").asInstanceOf[Int]
  private[this] val lexicalEntry = params("lexicalEntry").asInstanceOf[LexicalEntry]
  private[this] val field = params("field").asInstanceOf[Field]
  //private[this] val values = params("values").asInstanceOf[js.Array[Value]]
  private[this] val dictionaryId = CompositeId(dictionaryClientId, dictionaryObjectId)
  private[this] val perspectiveId = CompositeId(perspectiveClientId, perspectiveObjectId)
  private[this] val lexicalEntryId = CompositeId.fromObject(lexicalEntry)
  private[this] val fieldId = CompositeId.fromObject(field)

  private[this] var foundEntries = Seq[Seq[LexicalEntry]]()
  private[this] var dataTypes = Seq[TranslationGist]()
  private[this] var perspectiveFields = Seq[Field]()
  private[this] var dictionaries = Seq[Dictionary]()
  private[this] var perspectives = Seq[Perspective]()
  private[this] var searchDictionaries = Seq[Dictionary]()
  private[this] var searchPerspectives = Seq[Perspective]()

  override def spectrogramId: String = "#spectrogram-modal"

  scope.pageLoaded = false
  scope.searchQuery = ""
  scope.searchResults = js.Array[DictionaryTable]()
  scope.size = 10
  scope.pageNumber = 1
  scope.resultEntriesCount = -1

  @JSExport
  def getSource(entry: LexicalEntry): UndefOr[String]= {
    perspectives.find(p => p.clientId == entry.parentClientId && p.objectId == entry.parentObjectId).flatMap { perspective =>
      dictionaries.find(d => d.clientId == perspective.parentClientId && d.objectId == perspective.parentObjectId).map { dictionary =>
        s"${dictionary.translation} / ${perspective.translation}"
      }
    }.orUndefined
  }

  @JSExport
  def getSearchSource(entry: LexicalEntry): UndefOr[String]= {
    searchPerspectives.find(p => p.clientId == entry.parentClientId && p.objectId == entry.parentObjectId).flatMap { perspective =>
      searchDictionaries.find(d => d.clientId == perspective.parentClientId && d.objectId == perspective.parentObjectId).map { dictionary =>
        s"${dictionary.translation} / ${perspective.translation}"
      }
    }.orUndefined
  }

  @JSExport
  def search(): Unit = {
    foundEntries = Seq[Seq[LexicalEntry]]()
    backend.search(scope.searchQuery, None, tagsOnly = false) map { results =>
      //val entries = results map (_.lexicalEntry)
      foundEntries = results.map(_.lexicalEntry).groupBy(e => CompositeId(e.parentClientId, e.parentObjectId).getId).values.toSeq
      getPage(1)
    }
  }

  @JSExport
  def connect(entry: LexicalEntry): Unit = {
    backend.connectLexicalEntry(dictionaryId, perspectiveId, CompositeId.fromObject(field), lexicalEntry, entry).foreach { _ =>
      scope.dictionaryTable.addEntry(entry)
    }
  }

  @JSExport
  def remove(entry: LexicalEntry): Unit = {
    backend.disconnectLexicalEntry(dictionaryId, perspectiveId, CompositeId.fromObject(field), lexicalEntry, entry).foreach { _ =>
      scope.dictionaryTable.removeEntry(entry)
    }
  }

  @JSExport
  def close() = {
    instance.dismiss(())
  }

  @JSExport
  def editGroupingTag(entry: LexicalEntry, field: Field, values: js.Array[Value]): Unit = {

    perspectives.find(p => p.clientId == entry.parentClientId && p.objectId == entry.parentObjectId).flatMap { perspective =>
      dictionaries.find(d => d.clientId == perspective.parentClientId && d.objectId == perspective.parentObjectId).map { dictionary =>

        val options = ModalOptions()
        options.templateUrl = "/static/templates/modal/editGroupingTag.html"
        options.controller = "EditGroupingTagModalController"
        options.backdrop = false
        options.keyboard = false
        options.size = "lg"
        options.resolve = js.Dynamic.literal(
          params = () => {
            js.Dynamic.literal(
              dictionaryClientId = dictionary.clientId,
              dictionaryObjectId = dictionary.objectId,
              perspectiveClientId = perspective.clientId,
              perspectiveObjectId = perspective.objectId,
              lexicalEntry = entry.asInstanceOf[js.Object],
              field = field.asInstanceOf[js.Object],
              values = values.asInstanceOf[js.Object]
            )
          }
        ).asInstanceOf[js.Dictionary[Any]]

        val instance = modal.open[Unit](options)
        instance.result map { _ =>

        }
      }
    }
  }

  @JSExport
  def viewGroupingTag(entry: LexicalEntry, field: Field, values: js.Array[Value]): Unit = {

    perspectives.find(p => p.clientId == entry.parentClientId && p.objectId == entry.parentObjectId).flatMap { perspective =>
      dictionaries.find(d => d.clientId == perspective.parentClientId && d.objectId == perspective.parentObjectId).map { dictionary =>

        val options = ModalOptions()
        options.templateUrl = "/static/templates/modal/viewGroupingTag.html"
        options.controller = "EditGroupingTagModalController"
        options.backdrop = false
        options.keyboard = false
        options.size = "lg"
        options.resolve = js.Dynamic.literal(
          params = () => {
            js.Dynamic.literal(
              dictionaryClientId = dictionary.clientId,
              dictionaryObjectId = dictionary.objectId,
              perspectiveClientId = perspective.clientId,
              perspectiveObjectId = perspective.objectId,
              lexicalEntry = entry.asInstanceOf[js.Object],
              field = field.asInstanceOf[js.Object],
              values = values.asInstanceOf[js.Object]
            )
          }
        ).asInstanceOf[js.Dictionary[Any]]

        val instance = modal.open[Unit](options)
        instance.result map { _ =>

        }

      }
    }
    ()
  }

  @JSExport
  def range() = {
    (1 to scala.math.ceil(foundEntries.size.toDouble / scope.size).toInt by 1).toSeq.toJSArray
  }

  @JSExport
  def getPage(p: Int): Unit = {
    scope.pageLoaded = false
    val offset = (p - 1) * scope.size
    val entries = foundEntries.slice(offset, offset + scope.size)

    // get perspectives
    Future.sequence(entries.map { e => backend.getPerspective(CompositeId(e.head.parentClientId, e.head.parentObjectId)) }) map { perspectives =>
      searchPerspectives = perspectives

      // get dictionaries
      Future.sequence(perspectives.map { p => backend.getDictionary(CompositeId(p.parentClientId, p.parentObjectId)) }) map { dictionaries =>
        searchDictionaries = dictionaries

        // get fields
        Future.sequence(perspectives.map { p =>
          backend.getFields(CompositeId(p.parentClientId, p.parentObjectId), CompositeId.fromObject(p)).map { fields =>
            DictionaryTable.build(fields, dataTypes, entries.find(e => e.head.parentClientId == p.clientId && e.head.parentObjectId == p.objectId).get)
          }
        }).foreach { tables =>
          scope.searchResults = tables.toJSArray
          scope.pageLoaded = true
          scope.pageNumber = p
        }
      }
    }
  }



  load(() => {
    backend.dataTypes() flatMap { allDataTypes =>
      dataTypes = allDataTypes
      // get fields of main perspective
      backend.getFields(dictionaryId, perspectiveId) flatMap { fields =>
        perspectiveFields = fields
        backend.connectedLexicalEntries(lexicalEntryId, fieldId) map { connectedEntries =>
          scope.dictionaryTable = DictionaryTable.build(perspectiveFields, dataTypes, connectedEntries)

          Future.sequence(connectedEntries.map { e => backend.getPerspective(CompositeId(e.parentClientId, e.parentObjectId))}) map { connectedPerspectives =>
            perspectives = connectedPerspectives

            Future.sequence(connectedPerspectives.map { p => backend.getDictionary(CompositeId(p.parentClientId, p.parentObjectId))}) map { connectedDictionaries =>
              dictionaries = connectedDictionaries
            }
          }
        }
      }
    }
  })


  override protected def onModalClose(): Unit = {
    waveSurfer.foreach(w => w.destroy())
    super.onModalClose()
  }

  override protected def onStartRequest(): Unit = {
    scope.pageLoaded = false
  }

  override protected def onCompleteRequest(): Unit = {
    scope.pageLoaded = true
  }
}