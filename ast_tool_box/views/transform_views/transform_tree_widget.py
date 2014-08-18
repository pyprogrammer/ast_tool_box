__author__ = 'Chick Markley'

import types
import ast
from ast_tool_box.views.editor_widget import EditorPane
from ast_tool_box.views.search_widget import SearchLineEdit

from ast_tool_box.models.transform_models.transform_file import AstTransformItem, CodeGeneratorItem

from PySide import QtGui, QtCore

DEBUGGING = False


class TransformTreeWidgetItem(QtGui.QTreeWidgetItem):
    """
    connects a gui tree item with the corresponding node in the actual ast tree
    """
    def __init__(self, parent, name=None, source=None):
        super(TransformTreeWidgetItem, self).__init__(parent)
        self.name = name
        self.source = source

    def picked(self):
        print("got selected %s" % self.name)


class TransformTreeWidget(QtGui.QTreeWidget):
    """
    displays an ast as a tree widget
    """
    COL_NODE = 0
    COL_FIELD = 1
    COL_CLASS = 2
    COL_VALUE = 3
    COL_POS = 4
    COL_HIGHLIGHT = 5

    expand_all_at_create = True

    def __init__(self, transform_presenter=None, transform_pane=None):
        super(TransformTreeWidget, self).__init__()

        self.transform_presenter = transform_presenter
        self.transform_pane = transform_pane

        self.setColumnCount(2)
        self.setHeaderLabels(["Transforms"])
        self.header().resizeSection(TransformTreeWidget.COL_NODE, 800)
        self.header().setStretchLastSection(True)

        self.transform_signal = QtCore.Signal(int)

        self.expand_descendants_action = QtGui.QAction(
            "&Expand all children",
            self,
            statusTip="Expand all descendant nodes",
            triggered=self.expand_descendants
        )
        self.itemClicked.connect(self.clicked)
        self.itemDoubleClicked.connect(self.double_clicked)

    @QtCore.Slot(TransformTreeWidgetItem)
    def clicked(self, item):
        print("click %s" % item)
        self.transform_pane.load_editor_from(item)

    @QtCore.Slot(TransformTreeWidgetItem)
    def double_clicked(self, info):
        print("doubleclick on %s" % info)
        print("doubleclick on %s" % self.currentItem())
        print("comparing to %s" % AstTransformItem)
        print("comparing to %s" % AstTransformItem)

        if isinstance(self.currentItem().source, AstTransformItem) or\
                isinstance(self.currentItem().source, CodeGeneratorItem):
            self.transform_presenter.apply_current_transform()
        else:
            self.transform_pane.show_error("Only works for Ast Transforms and Code Generators")

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self.expand_descendants_action)

        sub_menu = QtGui.QMenu(self)
        sub_menu.setTitle("Available transformers")

        for transform_item in self.transform_presenter.transform_items():
            sub_menu_action = TransformerAction(transform_item=transform_item, ast_tree_widget=self)
            sub_menu.addAction(sub_menu_action)

        menu.addMenu(sub_menu)
        menu.exec_(event.globalPos())

    def transform_current_ast(self, name):
        transformer = self.ast_transformers.get_instance_by_name(name)
        self.main_window.add_tree_tab(transformer=transformer)

    def expand_descendants(self, item=None):
        """Expand all descendants of the current item"""
        if item is None:
            print("item is none")
            item = self.currentItem()
            print("item is %s" % item)

        item.setExpanded(True)
        for child_index in range(item.childCount()):
            self.expand_descendants(item.child(child_index))

    def collapse_descendants(self, item=None):
        """Expand all descendants of the current item"""
        if item is None:
            item = self.currentItem()

        item.setExpanded(False)
        for child_index in range(item.childCount()):
            self.collapse_descendants(item.child(child_index))

    def rebuild(self, transform_file):
        file_node = None
        for index in range(self.topLevelItemCount()):
            wi = self.topLevelItem(index)
            if wi.source is transform_file:
                file_node = wi
                break

        if not file_node:
            print("Could not find %s" % transform_file)

        def remove_children(node):
            for child_index in xrange(node.childCount()-1, -1, -1):
                print("removing child %d from node %s" % (child_index, node))
                remove_children(node.child(child_index))
                node.takeChild(child_index)

        remove_children(file_node)
        self.build_children(transform_file, file_node)
        self.expandToDepth(100)

    def build_children(self, transform_file, file_node):
        first_node = None
        if len(transform_file.node_transforms) > 0:
            transforms_node = TransformTreeWidgetItem(file_node)
            transforms_node.setText(
                TransformTreeWidget.COL_NODE,
                "ast.NodeTransformer : (%d)" % len(transform_file.node_transforms)
            )
            for transform in transform_file.node_transforms:
                transform_node = TransformTreeWidgetItem(transforms_node, name=transform.name, source=transform)
                if not first_node:
                    first_node = transform_node
                transform_node.setText(TransformTreeWidget.COL_NODE, transform.name())
                # print("loaded transform to tree %s" % transform.name)
                transform_node.setToolTip(TransformTreeWidget.COL_NODE, transform.doc)
        else:
            if transform_file.load_error_info:
                first_node = file_node

        if len(transform_file.code_generators) > 0:
            code_generators_node = TransformTreeWidgetItem(file_node)
            code_generators_node.setText(
                TransformTreeWidget.COL_NODE,
                "ctree.CodeGenVisitor : (%d)" % len(transform_file.code_generators)
            )
            print("%d code_generators" % len(transform_file.code_generators))

            for code_generator in transform_file.code_generators:
                code_generator_node = TransformTreeWidgetItem(
                    code_generators_node,
                    name=code_generator.name,
                    source=code_generator
                )
                if not first_node:
                    first_node = code_generator_node
                code_generator_node.setText(TransformTreeWidget.COL_NODE, code_generator.name())
                code_generator_node.setToolTip(TransformTreeWidget.COL_NODE, code_generator.doc)

        return first_node


    def build(self, transform_files):
        self.clear()

        first_node = None
        for transform_file in transform_files:
            file_node = TransformTreeWidgetItem(self, name=transform_file.base_name, source=transform_file)
            file_node.setText(
                TransformTreeWidget.COL_NODE,
                "%s (%s)" % (transform_file.base_name, transform_file.package_name)
            )
            file_node.setToolTip(TransformTreeWidget.COL_NODE, transform_file.path)
            node = self.build_children(transform_file, file_node)
            if not first_node:
                first_node = node

        self.expandToDepth(100)
        if first_node:
            self.setCurrentItem(first_node)
            self.transform_pane.load_editor_from(self.currentItem())


class TransformerAction(QtGui.QAction):
    def __init__(self, transform_item, ast_tree_widget, **kwargs):
        super(TransformerAction, self).__init__(transform_item.name(), ast_tree_widget, **kwargs)
        self.ast_tree_widget = ast_tree_widget
        self.transform_item = transform_item
        self.text = transform_item.name()
        self.triggered.connect(self.do_transform)

    def do_transform(self):
        print("Triggered with string %s" % self.text)
        self.ast_tree_widget.transform_presenter.apply_transform(
            code_item=self.ast_tree_widget.currentItem().ast_node,
            transform_item=self.transform_item
        )

