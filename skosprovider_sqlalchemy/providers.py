# -*- coding: utf-8 -*-

import logging
log = logging.getLogger(__name__)

from skosprovider.providers import VocabularyProvider

from skosprovider.skos import (
    Concept,
    Collection,
    Label
)

from skosprovider_sqlalchemy.models import (
    Thing,
    Concept as ConceptModel,
    Label as LabelModel
)

from sqlalchemy.orm import (
    joinedload,
)

from sqlalchemy.orm.exc import (
    NoResultFound
)


class SQLAlchemyProvider(VocabularyProvider):

    def __init__(self, metadata, session):
        super(SQLAlchemyProvider, self).__init__(metadata)
        self.conceptscheme_id = metadata.get('conceptscheme_id', metadata.get('id'))
        self.session = session

    def _from_thing(self, thing):
        if thing.type and thing.type == 'collection':
            return Collection(
                thing.id,
                [Label(l.label, l.labeltype_id, l.language_id) for l in thing.labels],
                thing.members if hasattr(thing, 'members') else []
            )
        else:
            return Concept(
                thing.id,
                [Label(l.label, l.labeltype_id, l.language_id) for l in thing.labels],
                thing.notes if hasattr(thing, 'notes') else [],
                thing.broader if hasattr(thing, 'broader') else [],
                thing.narrower if hasattr(thing, 'narrower') else [],
                thing.related if hasattr(thing, 'related') else [],
            )

    def get_by_id(self, id):
        try:
            thing = self.session\
                        .query(Thing)\
                        .filter(Thing.id == id, 
                                Thing.conceptscheme_id == self.conceptscheme_id
                        ).one()
        except NoResultFound:
            return False
        return self._from_thing(thing)

    def find(self, query, **kwargs):
        log.debug(query)
        lan = self._get_language(**kwargs)
        q = self.session\
                .query(Thing)\
                .options(joinedload('labels'))\
                .filter(Thing.conceptscheme_id == self.conceptscheme_id)
        if 'type' in query and query['type'] in ['concept', 'collection']:
            q = q.filter(Thing.type == query['type'])
        if 'label' in query:
            q = q.filter(Thing.labels.any(LabelModel.label.ilike('%' + query['label'].lower() + '%')))
        if 'collection' in query:
            coll = self.get_by_id(query['collection']['id'])
            if not coll or not isinstance(coll, Collection):
                raise ValueError(
                    'You are searching for items in an unexisting collection.'
                )
            q = q.filter(Thing.collections.any(Thing.id==query['collection']['id']))
        all = q.all()
        return [{'id': c.id, 'label': str(c.label(lan)) if c.label(lan) is not None else None} for c in all]

    def get_all(self, **kwargs):
        all = self.session\
                  .query(Thing)\
                  .options(joinedload('labels'))\
                  .filter(Thing.conceptscheme_id == self.conceptscheme_id)\
                  .all()
        lan = self._get_language(**kwargs)
        return [{'id': c.id, 'label': str(c.label(lan)) if c.label(lan) is not None else None} for c in all]

    def expand_concept(self, id):
        return self.expand(id)

    def expand(self, id):
        return [id]