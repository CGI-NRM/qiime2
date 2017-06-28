# ----------------------------------------------------------------------------
# Copyright (c) 2016-2017, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import collections
import concurrent.futures
import inspect
import unittest
import uuid

import qiime2.plugin
from qiime2.core.type import MethodSignature, Int
from qiime2.sdk import Artifact, Method, Results

from qiime2.core.testing.method import (concatenate_ints, merge_mappings,
                                        split_ints, params_only_method,
                                        no_input_method)
from qiime2.core.testing.type import IntSequence1, IntSequence2, Mapping
from qiime2.core.testing.util import get_dummy_plugin


# TODO refactor these tests along with Visualizer tests to remove duplication.
class TestMethod(unittest.TestCase):
    def setUp(self):
        self.plugin = get_dummy_plugin()

        self.concatenate_ints_sig = MethodSignature(
            concatenate_ints,
            inputs={
                'ints1': IntSequence1 | IntSequence2,
                'ints2': IntSequence1,
                'ints3': IntSequence2
            },
            parameters={
                'int1': qiime2.plugin.Int,
                'int2': qiime2.plugin.Int
            },
            outputs=[
                ('concatenated_ints', IntSequence1)
            ]
        )

        self.split_ints_sig = MethodSignature(
            split_ints,
            inputs={
                'ints': IntSequence1
            },
            parameters={},
            outputs=[
                ('left', IntSequence1),
                ('right', IntSequence1)
            ]
        )

    def test_private_constructor(self):
        with self.assertRaisesRegex(NotImplementedError,
                                    'Method constructor.*private'):
            Method()

    def test_from_function_with_artifacts_and_parameters(self):
        method = self.plugin.methods['concatenate_ints']

        self.assertEqual(method.id, 'concatenate_ints')
        self.assertEqual(method.signature, self.concatenate_ints_sig)
        self.assertEqual(method.name, 'Concatenate integers')
        self.assertTrue(
            method.description.startswith('This method concatenates integers'))
        self.assertTrue(
            method.source.startswith('\n```python\ndef concatenate_ints('))

    def test_from_function_with_multiple_outputs(self):
        method = self.plugin.methods['split_ints']

        self.assertEqual(method.id, 'split_ints')

        exp_sig = MethodSignature(
            split_ints,
            inputs={
                'ints': IntSequence1
            },
            parameters={},
            outputs=[
                ('left', IntSequence1),
                ('right', IntSequence1)
            ]
        )
        self.assertEqual(method.signature, exp_sig)

        self.assertEqual(method.name, 'Split sequence of integers in half')
        self.assertTrue(
            method.description.startswith('This method splits a sequence'))
        self.assertTrue(
            method.source.startswith('\n```python\ndef split_ints('))

    def test_from_function_without_parameters(self):
        method = self.plugin.methods['merge_mappings']

        self.assertEqual(method.id, 'merge_mappings')

        exp_sig = MethodSignature(
            merge_mappings,
            inputs={
                'mapping1': Mapping,
                'mapping2': Mapping
            },
            parameters={},
            outputs=[
                ('merged_mapping', Mapping)
            ]
        )
        self.assertEqual(method.signature, exp_sig)

        self.assertEqual(method.name, 'Merge mappings')
        self.assertTrue(
            method.description.startswith('This method merges two mappings'))
        self.assertTrue(
            method.source.startswith('\n```python\ndef merge_mappings('))

    def test_from_function_with_parameters_only(self):
        method = self.plugin.methods['params_only_method']

        self.assertEqual(method.id, 'params_only_method')

        exp_sig = MethodSignature(
            params_only_method,
            inputs={},
            parameters={
                'name': qiime2.plugin.Str,
                'age': qiime2.plugin.Int
            },
            outputs=[
                ('out', Mapping)
            ]
        )
        self.assertEqual(method.signature, exp_sig)

        self.assertEqual(method.name, 'Parameters only method')
        self.assertTrue(
            method.description.startswith('This method only accepts'))
        self.assertTrue(
            method.source.startswith('\n```python\ndef params_only_method('))

    def test_from_function_without_inputs_or_parameters(self):
        method = self.plugin.methods['no_input_method']

        self.assertEqual(method.id, 'no_input_method')

        exp_sig = MethodSignature(
            no_input_method,
            inputs={},
            parameters={},
            outputs=[
                ('out', Mapping)
            ]
        )
        self.assertEqual(method.signature, exp_sig)

        self.assertEqual(method.name, 'No input method')
        self.assertTrue(
            method.description.startswith('This method does not accept any'))
        self.assertTrue(
            method.source.startswith('\n```python\ndef no_input_method('))

    def test_is_callable(self):
        self.assertTrue(callable(self.plugin.methods['concatenate_ints']))

    def test_callable_properties(self):
        concatenate_ints = self.plugin.methods['concatenate_ints']
        merge_mappings = self.plugin.methods['merge_mappings']

        concatenate_exp = {
            'int2': Int, 'ints2': IntSequence1, 'return': (IntSequence1,),
            'int1': Int, 'ints3': IntSequence2,
            'ints1': IntSequence1 | IntSequence2}
        merge_exp = {
            'mapping2': Mapping, 'mapping1': Mapping, 'return': (Mapping,)}

        mapper = {
            concatenate_ints: concatenate_exp,
            merge_mappings: merge_exp}

        for method, exp in mapper.items():
            self.assertEqual(method.__call__.__name__, '__call__')
            self.assertEqual(method.__call__.__annotations__, exp)
            self.assertFalse(hasattr(method.__call__, '__wrapped__'))

    def test_async_properties(self):
        concatenate_ints = self.plugin.methods['concatenate_ints']
        merge_mappings = self.plugin.methods['merge_mappings']

        concatenate_exp = {
            'int2': Int, 'ints2': IntSequence1, 'return': (IntSequence1,),
            'int1': Int, 'ints3': IntSequence2,
            'ints1': IntSequence1 | IntSequence2}
        merge_exp = {
            'mapping2': Mapping, 'mapping1': Mapping, 'return': (Mapping,)}

        mapper = {
            concatenate_ints: concatenate_exp,
            merge_mappings: merge_exp}

        for method, exp in mapper.items():
            self.assertEqual(method.async.__name__, 'async')
            self.assertEqual(method.async.__annotations__, exp)
            self.assertFalse(hasattr(method.async, '__wrapped__'))

    def test_callable_and_async_signature_with_artifacts_and_parameters(self):
        # Signature with input artifacts and parameters (i.e. primitives).
        concatenate_ints = self.plugin.methods['concatenate_ints']

        for callable_attr in '__call__', 'async':
            signature = inspect.Signature.from_callable(
                getattr(concatenate_ints, callable_attr))
            parameters = list(signature.parameters.items())

            kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
            exp_parameters = [
                ('ints1', inspect.Parameter(
                    'ints1', kind, annotation=IntSequence1 | IntSequence2)),
                ('ints2', inspect.Parameter(
                    'ints2', kind, annotation=IntSequence1)),
                ('ints3', inspect.Parameter(
                    'ints3', kind, annotation=IntSequence2)),
                ('int1', inspect.Parameter(
                    'int1', kind, annotation=Int)),
                ('int2', inspect.Parameter(
                    'int2', kind, annotation=Int))
            ]

            self.assertEqual(parameters, exp_parameters)

    def test_callable_and_async_signature_with_no_parameters(self):
        # Signature without parameters (i.e. primitives), only input artifacts.
        method = self.plugin.methods['merge_mappings']

        for callable_attr in '__call__', 'async':
            signature = inspect.Signature.from_callable(
                getattr(method, callable_attr))
            parameters = list(signature.parameters.items())

            kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
            exp_parameters = [
                ('mapping1', inspect.Parameter(
                    'mapping1', kind, annotation=Mapping)),
                ('mapping2', inspect.Parameter(
                    'mapping2', kind, annotation=Mapping))
            ]

            self.assertEqual(parameters, exp_parameters)

    def test_call_with_artifacts_and_parameters(self):
        concatenate_ints = self.plugin.methods['concatenate_ints']

        artifact1 = Artifact.import_data(IntSequence1, [0, 42, 43])
        artifact2 = Artifact.import_data(IntSequence2, [99, -22])

        result = concatenate_ints(artifact1, artifact1, artifact2, 55, 1)

        # Test properties of the `Results` object.
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result, Results)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.concatenated_ints.view(list),
                         [0, 42, 43, 0, 42, 43, 99, -22, 55, 1])

        result = result[0]

        self.assertIsInstance(result, Artifact)
        self.assertEqual(result.type, IntSequence1)

        self.assertIsInstance(result.uuid, uuid.UUID)

        # Can retrieve multiple views of different type.
        exp_list_view = [0, 42, 43, 0, 42, 43, 99, -22, 55, 1]
        self.assertEqual(result.view(list), exp_list_view)
        self.assertEqual(result.view(list), exp_list_view)

        exp_counter_view = collections.Counter(
            {0: 2, 42: 2, 43: 2, 99: 1, -22: 1, 55: 1, 1: 1})
        self.assertEqual(result.view(collections.Counter),
                         exp_counter_view)
        self.assertEqual(result.view(collections.Counter),
                         exp_counter_view)

        # Accepts IntSequence1 | IntSequence2
        artifact3 = Artifact.import_data(IntSequence2, [10, 20])
        result, = concatenate_ints(artifact3, artifact1, artifact2, 55, 1)

        self.assertEqual(result.type, IntSequence1)
        self.assertEqual(result.view(list),
                         [10, 20, 0, 42, 43, 99, -22, 55, 1])

    def test_call_with_multiple_outputs(self):
        split_ints = self.plugin.methods['split_ints']

        artifact = Artifact.import_data(IntSequence1, [0, 42, -2, 43, 6])

        result = split_ints(artifact)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        for output_artifact in result:
            self.assertIsInstance(output_artifact, Artifact)
            self.assertEqual(output_artifact.type, IntSequence1)
            self.assertIsInstance(output_artifact.uuid, uuid.UUID)

        # Output artifacts have different UUIDs.
        self.assertNotEqual(result[0].uuid, result[1].uuid)

        # Index lookup.
        self.assertEqual(result[0].view(list), [0, 42])
        self.assertEqual(result[1].view(list), [-2, 43, 6])

        # Test properties of the `Results` object.
        self.assertIsInstance(result, Results)
        self.assertEqual(result.left.view(list), [0, 42])
        self.assertEqual(result.right.view(list), [-2, 43, 6])

    def test_call_with_no_parameters(self):
        merge_mappings = self.plugin.methods['merge_mappings']

        artifact1 = Artifact.import_data(Mapping, {'foo': 'abc', 'bar': 'def'})
        artifact2 = Artifact.import_data(Mapping, {'bazz': 'abc'})

        result = merge_mappings(artifact1, artifact2)

        # Test properties of the `Results` object.
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result, Results)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.merged_mapping.view(dict),
                         {'foo': 'abc', 'bar': 'def', 'bazz': 'abc'})

        result = result[0]

        self.assertIsInstance(result, Artifact)
        self.assertEqual(result.type, Mapping)

        self.assertIsInstance(result.uuid, uuid.UUID)

        self.assertEqual(result.view(dict),
                         {'foo': 'abc', 'bar': 'def', 'bazz': 'abc'})

    def test_call_with_parameters_only(self):
        params_only_method = self.plugin.methods['params_only_method']

        result, = params_only_method("Someone's Name", 999)

        self.assertIsInstance(result, Artifact)
        self.assertEqual(result.type, Mapping)
        self.assertIsInstance(result.uuid, uuid.UUID)
        self.assertEqual(result.view(dict), {"Someone's Name": '999'})

    def test_call_without_inputs_or_parameters(self):
        no_input_method = self.plugin.methods['no_input_method']

        result, = no_input_method()

        self.assertIsInstance(result, Artifact)
        self.assertEqual(result.type, Mapping)
        self.assertIsInstance(result.uuid, uuid.UUID)
        self.assertEqual(result.view(dict), {'foo': '42'})

    def test_call_with_optional_artifacts(self):
        method = self.plugin.methods['optional_artifacts_method']

        ints1 = Artifact.import_data(IntSequence1, [0, 42, 43])
        ints2 = Artifact.import_data(IntSequence1, [99, -22])
        ints3 = Artifact.import_data(IntSequence2, [43, 43])

        # No optional artifacts provided.
        obs = method(ints1, 42).output

        self.assertEqual(obs.view(list), [0, 42, 43, 42])

        # One optional artifact provided.
        obs = method(ints1, 42, optional1=ints2).output

        self.assertEqual(obs.view(list), [0, 42, 43, 42, 99, -22])

        # All optional artifacts provided.
        obs = method(
            ints1, 42, optional1=ints2, optional2=ints3, num2=111).output

        self.assertEqual(obs.view(list), [0, 42, 43, 42, 99, -22, 43, 43, 111])

        # Invalid type provided as optional artifact.
        with self.assertRaisesRegex(TypeError,
                                    'not a subtype of IntSequence1'):
            method(ints1, 42, optional1=ints3)

    def test_async(self):
        concatenate_ints = self.plugin.methods['concatenate_ints']

        artifact1 = Artifact.import_data(IntSequence1, [0, 42, 43])
        artifact2 = Artifact.import_data(IntSequence2, [99, -22])

        future = concatenate_ints.async(artifact1, artifact1, artifact2, 55, 1)

        self.assertIsInstance(future, concurrent.futures.Future)
        result = future.result()

        # Test properties of the `Results` object.
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result, Results)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.concatenated_ints.view(list),
                         [0, 42, 43, 0, 42, 43, 99, -22, 55, 1])

        result = result[0]

        self.assertIsInstance(result, Artifact)
        self.assertEqual(result.type, IntSequence1)

        self.assertIsInstance(result.uuid, uuid.UUID)

        # Can retrieve multiple views of different type.
        exp_list_view = [0, 42, 43, 0, 42, 43, 99, -22, 55, 1]
        self.assertEqual(result.view(list), exp_list_view)
        self.assertEqual(result.view(list), exp_list_view)

        exp_counter_view = collections.Counter(
            {0: 2, 42: 2, 43: 2, 99: 1, -22: 1, 55: 1, 1: 1})
        self.assertEqual(result.view(collections.Counter),
                         exp_counter_view)
        self.assertEqual(result.view(collections.Counter),
                         exp_counter_view)

        # Accepts IntSequence1 | IntSequence2
        artifact3 = Artifact.import_data(IntSequence2, [10, 20])
        future = concatenate_ints.async(artifact3, artifact1, artifact2, 55, 1)
        result, = future.result()

        self.assertEqual(result.type, IntSequence1)
        self.assertEqual(result.view(list),
                         [10, 20, 0, 42, 43, 99, -22, 55, 1])

    def test_async_with_multiple_outputs(self):
        split_ints = self.plugin.methods['split_ints']

        artifact = Artifact.import_data(IntSequence1, [0, 42, -2, 43, 6])

        future = split_ints.async(artifact)

        self.assertIsInstance(future, concurrent.futures.Future)
        result = future.result()

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        for output_artifact in result:
            self.assertIsInstance(output_artifact, Artifact)
            self.assertEqual(output_artifact.type, IntSequence1)

            self.assertIsInstance(output_artifact.uuid, uuid.UUID)

        # Output artifacts have different UUIDs.
        self.assertNotEqual(result[0].uuid, result[1].uuid)

        # Index lookup.
        self.assertEqual(result[0].view(list), [0, 42])
        self.assertEqual(result[1].view(list), [-2, 43, 6])

        # Test properties of the `Results` object.
        self.assertIsInstance(result, Results)
        self.assertEqual(result.left.view(list), [0, 42])
        self.assertEqual(result.right.view(list), [-2, 43, 6])

    def test_docstring(self):
        method = self.plugin.methods['split_ints']
        exp = "QIIME 2 Method"
        self.assertEqual(exp, method.__doc__)
        obs = method.__call__.__doc__.split('\n')
        self.assertTrue(obs[0].startswith('Split sequence of integers'))
        self.assertEqual(len(obs[1]), 0)
        self.assertTrue(obs[2].startswith('This method splits'))
        self.assertTrue(obs[3].startswith('(left and'))


if __name__ == '__main__':
    unittest.main()
