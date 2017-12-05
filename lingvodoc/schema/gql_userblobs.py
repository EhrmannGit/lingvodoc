from os import unlink
import graphene

from lingvodoc.schema.gql_holders import (
    LingvodocObjectType,
    client_id_check,
    fetch_object,
    CompositeIdHolder,
    AdditionalMetadata,
    CreatedAt,
    MarkedForDeletion,
    UserId,
    Content,
    DataType,
    Name,
    RealStoragePath,
    del_object,
    ResponseError,
    LingvodocID
)
from lingvodoc.utils.creation import create_object

from lingvodoc.models import (
    Client as dbClient,
    User as dbUser,
    UserBlobs as dbUserBlobs,
    DBSession
)
import base64

from lingvodoc.views.v2.sociolinguistics import check_socio  # TODO: replace it

#from lingvodoc.schema.gql_entity import create_object
import csv
class UserBlobs(LingvodocObjectType):
    """
    #created_at          | timestamp without time zone | NOT NULL
    #object_id           | bigint                      | NOT NULL
    #client_id           | bigint                      | NOT NULL
    #marked_for_deletion | boolean                     | NOT NULL
    #user_id             | bigint                      |
    #name                | text                        | NOT NULL
    #content             | text                        | NOT NULL
    #real_storage_path   | text                        | NOT NULL
    #data_type           | text                        | NOT NULL
    #additional_metadata | jsonb                       |

    query myQuery { userblob(id: [907, 2]){
       id
      content
      data_type
      user_id
      created_at
      name
      real_storage_path
      }
    }

    """
    dbType = dbUserBlobs
    triumph = graphene.Boolean()


    class Meta:
        interfaces = (CompositeIdHolder,
                      AdditionalMetadata,
                      CreatedAt,
                      MarkedForDeletion,
                      UserId,
                      Content,
                      DataType,
                      Name,
                      RealStoragePath)



class CreateUserBlob(graphene.Mutation):
    """
    -F "blob=@sound.wav" -F 'query=mutation create_userblob{
    create_userblob(data_type: "sound"){
       userblob{
           id
           content
           name
           created_at
       }
    }
    }' http://localhost:6543/graphql
    """
    class Arguments:
        id = LingvodocID()
        data_type = graphene.String(required=True)  #(required=True)


    userblob = graphene.Field(UserBlobs)
    triumph = graphene.Boolean()


    @staticmethod
    @client_id_check()
    def mutate(root, info, **args):
        id = args.get('id')
        client_id = id[0] if id else info.context["client_id"]
        object_id = id[1] if id else None
        if not "variables.content" in info.context.request.POST:
            raise ResponseError(message="file not found")
        multiparted = info.context.request.POST.pop("variables.content")
        # multiparted = info.context.request.POST.pop("opearations")
        filename = multiparted.filename
        input_file = multiparted.file#multiparted.file

        class Object(object):
            pass

        blob = Object()
        blob.client_id = client_id
        client = DBSession.query(dbClient).filter_by(id=client_id).first()
        user = DBSession.query(dbUser).filter_by(id=client.user_id).first()
        #if args.get("data_type"):
        blob.data_type = args.get("data_type")

        blob.filename = filename



        current_user = DBSession.query(dbUser).filter_by(id=client.user_id).first()

        blob_object = dbUserBlobs(object_id=object_id,
                                client_id=blob.client_id,
                                name=filename,
                                data_type=blob.data_type,
                                user_id=current_user.id,
                                content=None,
                                real_storage_path=None)


        blob_object.real_storage_path, blob_object.content = create_object(info.context.request, input_file, blob_object, blob.data_type,
                                                                           blob.filename, json_input=False)

        if blob.data_type == "sociolinguistics":
            try:
                check_socio(blob_object.real_storage_path)
            except Exception as e:
                raise ResponseError(message=str(e))

        if blob.data_type == "starling/csv":
            try:
                input_file.seek(0)

                with input_file  as csvfile:
                    starling_fields = csvfile.readline().decode('utf-8').rstrip().split('|')
                    # starling_fields = csv.reader(csvfile, delimiter = '|')

                    if not blob_object.additional_metadata:
                        blob_object.additional_metadata = {}
                    blob_object.additional_metadata['starling_fields'] = starling_fields
            except Exception as e:
                raise ResponseError(message=str(e))
        current_user.userblobs.append(blob_object)
        DBSession.add(blob_object)
        #DBSession.add(current_user)
        DBSession.flush()
        userblob = UserBlobs(id = [blob_object.client_id, blob_object.object_id]) # TODO: more args
        return CreateUserBlob(userblob=userblob, triumph=True)

class DeleteUserBlob(graphene.Mutation):
    """
    mutation  {
        delete_userblob(id: [1199, 168]) {
            userblob {
                id
                content
                marked_for_deletion
            }
            triumph
        }
    }
    """
    class Arguments:
        id = LingvodocID(required=True)


    userblob = graphene.Field(UserBlobs)
    triumph = graphene.Boolean()


    @staticmethod
    def mutate(root, info, **args):
        id = args.get('id')
        client_id = id[0] if id else info.context["client_id"]
        object_id = id[1] if id else None

        blob = DBSession.query(dbUserBlobs).filter_by(client_id=client_id, object_id=object_id).first()
        if not blob:
            raise ResponseError(message="No such blob in the system'")
 
        filelocation = blob.real_storage_path
        del_object(blob)
        try:
            unlink(filelocation)
        except:
            # NOTE: intentionally not an error
            raise ResponseError(message="File can not be deleted physically; deleting from DMBS only.")
        DBSession.flush()
        userblob = UserBlobs(id = [blob.client_id, blob.object_id]) # TODO: more args
        return DeleteUserBlob(userblob=userblob, triumph=True)