from typing import Union, Iterable
from uuid import UUID, uuid4

import pytest

from freddie import Schema


class ModelMeta(Schema):
    size: int = 0
    description: str = ...

    class Config:
        default_readable_fields = {'description'}


class Model(Schema):
    id: Union[UUID, int] = ...
    title: str = ...
    content: str = ''
    meta: ModelMeta = {}


class ModelWithFieldsConf(Model):
    class Config:
        read_only_fields = {'id', 'invalid', 42}
        write_only_fields = {'meta', 'corrupted'}
        default_readable_fields = {'id', 'title', 'another'}


class ModelWithNested(Schema):
    nested: Iterable[Model]


class TestSchemaFields:
    def test_optional_schema_creation(self):
        optional_schema = Model.optional()
        instance = optional_schema()
        assert instance.id is None
        assert instance.title is None

    def test_read_only_fields_config(self):
        assert Model.get_read_only_fields() == set()
        assert Model.get_writable_fields() == {'id', 'title', 'content', 'meta'}
        assert ModelWithFieldsConf.get_read_only_fields() == {'id'}
        assert ModelWithFieldsConf.get_writable_fields() == {'title', 'content', 'meta'}

    def test_write_only_fields_config(self):
        assert Model.get_write_only_fields() == set()
        assert Model.get_readable_fields() == {'id', 'title', 'content', 'meta'}
        assert ModelWithFieldsConf.get_write_only_fields() == {'meta'}
        assert ModelWithFieldsConf.get_readable_fields() == {'id', 'title', 'content'}

    def test_default_readable_fields_config(self):
        assert Model.get_default_readable_fields() == {'id', 'title', 'content', 'meta'}
        assert ModelWithFieldsConf.get_default_readable_fields() == {'id', 'title'}

    def test_response_fields_configs(self):
        default_fields_config = {
            'id': set(), 'title': set(), 'content': set(), 'meta': {'description'}
        }
        full_fields_config = {**default_fields_config, 'meta': {'description', 'size'}}
        assert Model.get_default_response_fields_config() == default_fields_config
        assert Model.get_full_response_fields_config() == full_fields_config
        assert ModelWithFieldsConf.get_default_response_fields_config() == {
            'id': set(), 'title': set()
        }
        assert ModelWithFieldsConf.get_full_response_fields_config() == {
            'id': set(), 'title': set(), 'content': set()
        }


# Most simple case: single dict
model_data = {
    'id': 42, 'title': 'Title', 'content': 'Lorem', 'meta': {'description': 'that'}
}
model = Model(**model_data)


def datagenerator(as_dict: bool = True):
    for _ in range(3):
        yield model_data if as_dict else model


async def async_datagenerator(as_dict: bool = True):
    for _ in range(3):
        yield model_data if as_dict else model


# Iterables
model_data_list = list(datagenerator(as_dict=True))
model_data_genexpr = (datum for datum in datagenerator(as_dict=True))

# Case with complex data type
_uuid = uuid4()
model_data_ext = {**model_data, 'id': _uuid}
model_ext = Model(**model_data_ext)
model_data_ext_jsonable = {**model_data_ext, 'id': str(_uuid)}


@pytest.mark.asyncio
@pytest.mark.parametrize('data,expected', [
    (model_data, model_data),
    (model_data_list, model_data_list),
    (list(datagenerator(as_dict=False)), model_data_list),
    (model_data_genexpr, model_data_list),
    (datagenerator(as_dict=True), model_data_list),
    (datagenerator(as_dict=False), model_data_list),
    (async_datagenerator(as_dict=True), model_data_list),
    (async_datagenerator(as_dict=False), model_data_list),
    (model, model_data),
    (model_ext, model_data_ext_jsonable),
], ids=[
    'dict',
    'list_of_dicts',
    'list_of_models',
    'genexpr_of_dicts',
    'generator_of_dicts',
    'generator_of_models',
    'async_generator_of_dicts',
    'async_generator_of_models',
    'model_instance',
    'model_instance_uuid'
])
async def test_simple_serialization(data, expected):
    assert await Model.serialize(data) == expected


model_data_nested = {'nested': model_data_list}


@pytest.mark.asyncio
@pytest.mark.parametrize('data,expected', [
    (ModelWithNested(nested=list(datagenerator())), model_data_nested),
    (ModelWithNested(nested=list(datagenerator(as_dict=False))), model_data_nested),
    (ModelWithNested(nested=datagenerator()), model_data_nested),
    (ModelWithNested(nested=datagenerator(as_dict=False)), model_data_nested),
], ids=[
    'nested_list_of_dicts',
    'nested_list_of_models',
    'nested_generator_of_dicts',
    'nested_generator_of_models',
])
async def test_nested_serialization(data, expected):
    assert await ModelWithNested.serialize(data) == expected


conf_model_data = {
    'id': 43, 'title': 'Other title'
}
conf_model_data_extra = {'content': 'Ipsum'}
conf_model_data_extended = {**conf_model_data, **conf_model_data_extra}
conf_model = ModelWithFieldsConf(**conf_model_data)
conf_model_extended = ModelWithFieldsConf(**conf_model_data_extended)


@pytest.mark.asyncio
@pytest.mark.parametrize('data,fields,expected', [
    (conf_model_data, None, conf_model_data),
    (conf_model, None, conf_model_data),
    (conf_model_data_extra, {'content': {}, 'foo': {'bar'}}, conf_model_data_extra),
], ids=[
    'dict_no_fields',
    'model_instance_no_fields',
    'dict_with_fields',
])
async def test_configured_serialization(data, fields, expected):
    assert await ModelWithFieldsConf.serialize(data, fields=fields) == expected
