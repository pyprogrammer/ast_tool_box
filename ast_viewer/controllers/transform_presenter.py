from __future__ import print_function

import ast
import sys
from PySide import QtCore, QtGui

import ast_viewer.controllers as controllers
import ast_viewer.models.transform_models.transform_model as transform_model
from ast_viewer.controllers.tree_transform_controller import TreeTransformController
from ast_viewer.views.transform_views.transform_pane import TransformPane
from ctree.codegen import CodeGenVisitor
from ast_viewer.util import Util


class TransformPresenter(object):
    """
    coordinate between various transformer, either
    ast transformers or code generators
    have direct connection to a code code_presenter
    TODO: Do more investigation of managing transforms in separate namespace
    """
    def __init__(self, tree_transform_controller=None):
        assert isinstance(tree_transform_controller, TreeTransformController)

        self.code_presenter = None
        self.tree_transform_controller = tree_transform_controller
        self.transform_pane = TransformPane(transform_presenter=self)

        self.transforms_loaded = []
        self.transform_items = []
        self.transforms_by_name = {}

        self.load_transforms('ctree.transformations')
        self.load_transforms('ctree.c.codegen')
        self.load_transforms('ctree.ocl.codegen')
        self.load_transforms('ctree.omp.codegen')

        self.transform_pane.reload_list()

    def set_code_presenter(self, code_presenter):
        # assert isinstance(code_presenter, controllers.TransformPresenter)
        self.code_presenter = code_presenter

    def apply_transform(self, code_item, transform_item):
        self.code_presenter.apply_transform(code_item=code_item, transform_item=transform_item)

    def current_item(self):
        return self.transform_pane.current_item()

    def apply_current_transform(self):
        transform_item = self.current_item().transform_item
        code_item = self.code_presenter.current_item()
        self.apply_transform(code_item, transform_item)

    def clear(self):
        self.transform_items = []
        self.transforms_by_name = {}

    def count(self):
        """return current transforms"""
        return len(self.transform_items)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.transform_items[item]
        elif isinstance(item, str):
            return self.transforms_by_name[item]

    def get_valid_index(self, index):
        """
        convenience method for checking index
        if index is a string make it an int
        None returned if failed to convert or index out of range
        """
        if not isinstance(index, int):
            try:
                index = int(index)
            except ValueError:
                return None

        if index >= 0:
            if index < len(self.transform_items):
                return index
        return None

    def get_ast_transforms(self, module_name):
        """Use module_name to discover some transforms"""

        try:
            __import__(module_name)
            self.reload()
        except Exception as exception:
            print("cannot load %s message %s" % (module_name, exception.message))

    def reload(self):
        """rebuild list of all in memory subclasses of ast.NodeTransformer"""

        self.transform_items = map(
            lambda transform: transform_model.AstTransformItem(transform),
            ast.NodeTransformer.__subclasses__()
        )

        self.transform_items += map(
            lambda transform: transform_model.CodeGeneratorItem(transform),
            CodeGenVisitor.__subclasses__()
        )

        for transform_item in self.transform_items:
            print("loaded %s" % transform_item.name())
            self.transforms_by_name[transform_item.name()] = transform_item

    def get_instance_by_name(self, transform_name):
        transform_item = self.transforms_by_name[transform_name]
        return transform_item.get_instance()

    def __iter__(self):
        return iter(self.transform_items)

    def load_transforms_by_file_name(self, file_name):
        """Todo"""
        pass

    def load_transforms(self, key):
        self.transforms_loaded.append(key)

        path, package_name = Util.path_to_path_and_package(key)

        print("path %s package %s" % (path, package_name))

        if not path in sys.path:
            sys.path.append(path)

        self.get_ast_transforms(package_name)
        self.reload()

        print("AstTransformManager %s" % self)