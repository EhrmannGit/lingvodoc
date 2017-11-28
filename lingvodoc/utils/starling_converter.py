import collections
import datetime
from collections import defaultdict
from itertools import chain
import graphene
from lingvodoc.models import (
    Dictionary as dbDictionary,
    TranslationAtom as dbTranslationAtom,
    TranslationGist as dbTranslationGist,
    DBSession,
    Client as dbClient,
    Language as dbLanguage,
    User as dbUser,
    Field as dbField,
    DictionaryPerspective as dbDictionaryPerspective,
    BaseGroup as dbBaseGroup,
    Group as dbGroup,
    Organization as dbOrganization,
    UserBlobs as dbUserBlobs,
    LexicalEntry as dbLexicalEntry
)
from lingvodoc.utils.creation import create_gists_with_atoms, update_metadata, add_user_to_group
from lingvodoc.schema.gql_holders import (
    LingvodocObjectType,
    CommonFieldsComposite,
    StateHolder,
    TranslationHolder,
    fetch_object,
    del_object,
    client_id_check,
    ResponseError,
    ObjectVal,
    acl_check_by_id,
    LingvodocID,
    UserAndOrganizationsRoles
)

from lingvodoc.utils import statistics
from lingvodoc.utils.creation import (create_perspective,
                                      create_dbdictionary,
                                      create_dictionary_persp_to_field,
                                      edit_role)
from lingvodoc.utils.search import translation_gist_search
from lingvodoc.utils.creation import create_entity


def translation_gist_search_all(searchstring, gist_type):
        translationatom = DBSession.query(dbTranslationAtom) \
            .join(dbTranslationGist). \
            filter(dbTranslationAtom.content == searchstring,
                   dbTranslationAtom.locale_id == 2,
                   dbTranslationGist.type == gist_type) \
            .first()

        if translationatom and translationatom.parent:
            translationgist = translationatom.parent
            return translationgist

def get_field_id_by_name(field_name, gist_type="Service"):
    # TODO: move to utils
    gist = translation_gist_search_all(field_name, gist_type)
    if gist:
        field = DBSession.query(dbField).filter_by(translation_gist_client_id=gist.client_id, translation_gist_object_id=gist.object_id).first()
        return (field.client_id, field.object_id)

def csv_to_columns(path):
    import csv
    csv_file = open(path, "rb").read().decode("utf-8", "ignore")
    lines = [x.rstrip().split('|') for x in csv_file.split("\n")]
    column_dict = collections.OrderedDict()
    columns = lines[0]
    lines.pop()
    j = 0
    for line in lines:
        i = 0
        if not j:
            j=1
            continue
        for column in columns:
            if not column in column_dict:
                column_dict[column] = []
            column_dict[column].append(line[i])
            i += 1
    return column_dict

def starling_field_to_column(field, perspective_id, position_counter, ids):
    starling_type = field.get("starling_type")
    field_id = field.get("field_id")
    if starling_type == 1:
        persp_to_field = create_dictionary_persp_to_field(id=ids,
                         parent_id=perspective_id,
                         field_id=field_id,
                         upper_level=None,
                         link_id=None,
                         position=position_counter
                         )
        return persp_to_field
    elif starling_type == 2:
        # copy
        fake_id = field.get("fake_id")
        link_fake_id = field.get("link_fake_id")
        persp_to_field = create_dictionary_persp_to_field(id=ids,
                         parent_id=perspective_id,
                         field_id=field_id,
                         upper_level=None,
                         link_id=None,
                         position=position_counter
                         )
        return persp_to_field

#create_gists_with_atoms
def convert(info, starling_dictionaries):

    #starling_dictionaries=fake_starling
    ids = [info.context["client_id"], None]
    locale_id = info.context.get('locale_id')

    persp_fake_ids = dict()
    etymology_field_id = get_field_id_by_name("Etymology", "Field")
    relation_field_id = get_field_id_by_name("Relation", "Field")



    dictionary_id_links = collections.defaultdict(list)

    fake_id_dict = {}
    fake_link_dict = {}
    for starling_dictionary in starling_dictionaries:
        fields = starling_dictionary.get("field_map")
        blob_id_as_fake_id = starling_dictionary.get("blob_id")
        for field in fields:
            link_fake_id = field.get("link_fake_id")
            if not link_fake_id:
                continue
            dictionary_id_links[tuple(blob_id_as_fake_id)].append(tuple(link_fake_id))

    blob_to_perspective = dict()
    #perspective_to_collist = {}
    perspective_column_dict = {}
    # getting all values
    persp_to_starcolumns = dict()

    all_le = []
    all_entities = []
    persp_to_lexentry = collections.defaultdict(dict)
    copy_field_dict = collections.OrderedDict(dict)

    for starling_dictionary in starling_dictionaries:
        blob_id = starling_dictionary.get("blob_id")
        blob = DBSession.query(dbUserBlobs).filter_by(client_id=blob_id[0], object_id=blob_id[1]).first()
        column_dict = csv_to_columns(blob.real_storage_path)

        field_map = starling_dictionary.get("field_map")




        atoms_to_create = starling_dictionary.get("translation_atoms")
        #translation_gist_id = starling_dictionary.get("translation_gist_id")
        dictionary_translation_gist_id = create_gists_with_atoms(atoms_to_create, None, ids)
        parent_id = starling_dictionary.get("parent_id")

        dbdictionary_obj = create_dbdictionary(id=ids,
                                               parent_id=parent_id,
                                               translation_gist_id=dictionary_translation_gist_id)
        atoms_to_create = [{"locale_id": 2, "content": "PERSPECTIVE_NAME"}] #starling_dictionary.get("perspective_atoms")
        #persp_translation_gist_id = starling_dictionary.get("translation_gist_id")
        persp_translation_gist_id = create_gists_with_atoms(atoms_to_create, None, ids)
        dictionary_id = [dbdictionary_obj.client_id, dbdictionary_obj.object_id]
        new_persp = create_perspective(id=ids,
                                parent_id=dictionary_id,  # TODO: use all object attrs
                                translation_gist_id=persp_translation_gist_id
                                )
        perspective_column_dict[new_persp] = column_dict
        blob_to_perspective[tuple(blob_id)] = new_persp
        perspective_id = [new_persp.client_id, new_persp.object_id]
        fields = starling_dictionary.get("field_map")
        starlingname_to_column = collections.OrderedDict()

        position_counter = 1

        # perspective:field_id


        for field in fields:
            starling_type = field.get("starling_type")
            field_id = field.get("field_id")
            starling_name = field.get("starling_name")
            if starling_type == 1:
                persp_to_field = create_dictionary_persp_to_field(id=ids,
                                 parent_id=perspective_id,
                                 field_id=field_id,
                                 upper_level=None,
                                 link_id=None,
                                 position=position_counter
                                 )
                position_counter += 1
                starlingname_to_column[starling_name] = field_id
            elif starling_type == 2:
                # copy
                persp_to_field = create_dictionary_persp_to_field(id=ids,
                                 parent_id=perspective_id,
                                 field_id=field_id,
                                 upper_level=None,
                                 link_id=None,
                                 position=position_counter
                                 )
                position_counter += 1
                starlingname_to_column[starling_name] = field_id
                copy_field_dict[new_persp][field_id] = starling_name



        add_etymology = starling_dictionary.get("add_etymology")
        if add_etymology:
            persp_to_field = create_dictionary_persp_to_field(id=ids,
                             parent_id=perspective_id,
                             field_id=etymology_field_id,
                             upper_level=None,
                             link_id=None,
                             position=position_counter
                             )
            position_counter += 1
            #starlingname_to_column["ETYMOLOGY_PERSPECTIVE_TO_FIELD"] = etymology_field_id
        persp_to_field = create_dictionary_persp_to_field(id=ids,
                 parent_id=perspective_id,
                 field_id=relation_field_id,
                 upper_level=None,
                 link_id=None,
                 position=position_counter
                 )
        #starlingname_to_column["DIRECT_LINK_PERSPECTIVE_TO_FIELD"] = relation_field_id
        fields_marked_as_links = [x for x in fields if x.get("starling_type") == 3]
        for starling_column in starlingname_to_column:
            #if starling_column
            column = starlingname_to_column[starling_column]
        #for field in fields_marked_as_links:  #
        #    perspective_to_collist[new_persp] = fields_marked_as_links #
        persp_to_starcolumns[new_persp] = starlingname_to_column

        # blob_link -> perspective_link
        csv_data = perspective_column_dict[new_persp]
        collist = list(persp_to_starcolumns[new_persp])
        for numb in csv_data["NUMBER"]:
            numb = int(numb)
            lexentr = dbLexicalEntry(client_id=ids[0],
                                   parent=new_persp)
            all_le.append(lexentr)

            persp_to_lexentry[new_persp][numb] = lexentr
            for starling_column_name in starlingname_to_column:
                field_id = starlingname_to_column[starling_column_name]
                col_data = csv_data[starling_column_name][numb-1]
                new_ent = create_entity(id=ids,
                    parent_id=[lexentr.client_id, lexentr.object_id],
                    additional_metadata=None,
                    field_id=field_id,
                    self_id=None,
                    link_id=None, #
                    locale_id=2,
                    filename=None,
                    content=col_data,
                    registry=None,
                    request=None,
                    save_object=False)
                all_entities.append(new_ent)

    for starling_dictionary in starling_dictionaries:
        blob_id = starling_dictionary.get("blob_id")
        persp = blob_to_perspective[tuple(blob_id)]
        copy_field_dict[persp]
    # for persp in copy_field_dict:
    #     # fields
    #     field_to_starlig = copy_field_dict[persp]
    #     for field_id in field_to_starlig:
    #         starling_field = field_to_starlig[field_id]
    #     # target
    #     dictionary_id_links
    c = 0
    for lex in all_le:
        DBSession.add(lex)
        if not c % 10:
            DBSession.flush()
        c+=1
    c = 0
    for ent in all_entities:
        DBSession.add(ent)
        if not c % 10:
            DBSession.flush()

    # # lexical entry creation
    # for blob_id, links in dictionary_id_links.items():
    #     persp = blob_to_perspective[blob_id]
    #     persp = blob_to_perspective[blob_id]
    #     #new_links = [blob_to_perspective[x] for x in links if x in blob_to_perspective]
    four = 2+2
    #result = starlingname_to_column

