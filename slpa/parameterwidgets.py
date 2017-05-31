from imports import *
from collections import defaultdict
from parameters import *
import anytree

class ParameterTreeWidget(QTreeWidget):
    itemChecked = Signal(object, int)

    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.buttonGroups = defaultdict(list)
        self.itemClicked.connect(self.handleItemChanged)
        self.currentItemChanged.connect(self.handleItemChanged)
        self.currentItemChanged.connect(self.dialog.updateDisplayTree)

    def handleItemChanged(self, item, column):
        if item.parent() is None:
            return

        parent = self.findTopParent(item)
        # selectionLayout = getattr(self.dialog, parent.text(0)+'Layout')
        # selectionLayout.changeText(item.parent().text(0), item.text(0))

        for button in self.buttonGroups[item.parent().text(0)]:
            if button.text(0) == item.text(0):
                button.setCheckState(0, Qt.Checked)
                self.dialog.updateDisplayTree(button.text(0), item.parent().text(0), addToTree=True)
            else:
                button.setCheckState(0, Qt.Unchecked)
                self.dialog.updateDisplayTree(button.text(0), item.parent().text(0), addToTree=False)

    def findTopParent(self, item):
        parent = item.parent()
        while True:
            if parent.parent() is None:
                break
            else:
                parent = parent.parent()
        return parent


class ParameterSelectionsLayout(QHBoxLayout):

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.values = list()
        self.addWidget(QLabel(self.name))

    def addLabel(self, text):
        setattr(self, text+'Label', QLabel(text))
        self.values.append(text+'Label')
        self.addWidget(getattr(self, text+'Label'))

    def changeText(self, labelName, newText):
        widgetName = labelName+'Label'
        for value in self.values:
            if value == widgetName:
                getattr(self, widgetName).setText(' : '.join([labelName, newText]))
                break

class ParameterDialog(QDialog):
    updateAfterClosing = Signal(bool, anytree.Node)

    def __init__(self, model):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle('Select Parameters')
        self.accepted = False
        layout = QVBoxLayout()
        self.model = model
        parameterLayout = QHBoxLayout()
        self.tree = ParameterTreeWidget(self)
        self.displayTree = anytree.Node('Selected Parameters', parent=None)
        self.selectionLayout = QVBoxLayout()
        self.displayTreeWidget = QLabel()
        for p in model.tree.children:
            # setattr(self, p.name + 'Layout', ParameterSelectionsLayout(p.name))
            # self.selectionLayout.addLayout(getattr(self, p.name + 'Layout'))
            displayNode = anytree.Node(p.name, parent=self.displayTree)
            parent = ParameterTreeWidgetItem(self.tree)
            parent.setText(0, p.name)
            self.addChildren(parent, p, p.name, displayNode)#, getattr(self, p.name + 'Layout'))
        self.generateDisplayTreeText()
        self.selectionLayout.addWidget(self.displayTreeWidget)
        parameterLayout.addWidget(self.tree)
        parameterLayout.addLayout(self.selectionLayout)

        terminalNodesLayout = QVBoxLayout()
        self.terminalNodesLabel = QLabel('No parameters selected')
        terminalNodesLayout.addWidget(self.terminalNodesLabel)
        parameterLayout.addLayout(terminalNodesLayout)

        buttonLayout = QHBoxLayout()
        okButton = QPushButton('OK')
        cancelButton = QPushButton('Cancel')
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        layout.addLayout(parameterLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    def accept(self):
        self.updateAfterClosing.emit(True, self.displayTree)
        super().accept()

    def reject(self):
        self.updateAfterClosing.emit(False, self.displayTree)
        super().reject()

    def generateDisplayTreeText(self):
        treeText = list()
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            treeText.append("{}{}".format(pre, node.name))
        treeText = '\n'.join(treeText)
        self.displayTreeWidget.setText(treeText)

    def updateDisplayTree(self, item, parent, addToTree=None):
        if addToTree is None:
            return #in this case user clicked text, not a checkbox

        if addToTree:
            parentNode = [node for node in anytree.PostOrderIter(self.displayTree) if node.name == parent][0]
            for child in parentNode.children:
                child.parent = None
                del child
            node = anytree.Node(item, parent=parentNode)

        treeText = list()
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            treeText.append("{}{}".format(pre, node.name))
        self.displayTreeWidget.setText('\n'.join(treeText))
        self.updateTerminalNodes()

    def updateTerminalNodes(self):
        text = list()
        true_children = [node.name for pre, fill, node in anytree.RenderTree(self.model.tree) if node.is_leaf]
        for pre, fill, node in anytree.RenderTree(self.displayTree):
            if node.is_leaf and node.name in true_children:
                text.append(node.name)
        text = '\n'.join(text)
        self.terminalNodesLabel.setText(text)

    def addChildren(self, parentWidget, parentParameter, top_parameter, displayNode):
        buttonGroup = list()
        appendGroup = False
        for c in parentParameter.children:
            child = ParameterTreeWidgetItem(parentWidget)
            # if isinstance(c, Parameter):
            if not c.is_leaf:
                #it's a non-terminal node
                newDisplayNode = anytree.Node(c.name, parent=displayNode)
                child.setText(0, c.name)
                self.addChildren(child, c, top_parameter, newDisplayNode)#, selectionLayout)
            else:
                #it's a terminal node
                child.setText(0, c.name)
                child.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)
                child.setCheckState(0, Qt.Unchecked)
                buttonGroup.append(child)
                appendGroup = True

        if appendGroup:
            self.tree.buttonGroups[parentParameter.name].extend(buttonGroup)
            # selectionLayout.addLabel(buttonGroup[0].parent().text(0))
            #every member of the buttonGroup has the same parent, so just grab an arbitrary one and use that information


class ParameterTreeWidgetItem(QTreeWidgetItem):

    def __init__(self, parent):
        super().__init__(parent)

    def setData(self, column, role, value):
        state = self.checkState(column)
        super().setData(column, role, value)
        if (role == Qt.CheckStateRole and
            state != self.checkState(column)):
            treewidget = self.treeWidget()
            if treewidget is not None:
                treewidget.itemChecked.emit(self, column)

class ParameterTreeModel():

    def __init__(self, parameters):
        self.tree = anytree.Node('Parameters', parent=None)
        for p in parameters:
            parameterNode = anytree.Node(p.name, parent=self.tree)
            setattr(self, p.name, parameterNode)
            for child in p.children:
                self.addNode(child, parameterNode)

    def addNode(self, parameter, parentNode):
        if hasattr(parameter, 'children'):
            newNode = anytree.Node(parameter.name, parent=parentNode)
            for c in parameter.children:
                self.addNode(c, newNode)
        else:
            newNode = anytree.Node(parameter, parent=parentNode)

    def __iter__(self):
        for node in self.tree.children:
            yield node.name

# treeModel = ParameterTreeModel([Quality, MajorMovement, MajorLocation])
# dialog = ParameterDialog([Quality, MajorMovement, MajorLocation])

# print([(node.name, node.parent.name) for node in anytree.PostOrderIter(treeModel.tree, filter_=lambda x: x.is_leaf)])
# for pre, fill, node in anytree.RenderTree(treeModel.tree):
#     print("{}{}".format(pre, node.name))
#
# import pickle
# import os
# from binary import load_binary, save_binary
# save_binary(treeModel, os.path.join(os.getcwd(),'tree.tree'))
# treeModel = load_binary(os.path.join(os.getcwd(), 'tree.tree'))
# for pre, fill, node in anytree.RenderTree(treeModel.tree):
#     print("{}{}".format(pre, node.name))
# treeModel.addNode('Spam', treeModel.tree)
# # tree.addNode('Vikings', tree.)
# save_binary(treeModel, os.path.join(os.getcwd(),'tree.tree'))
# tree = load_binary(os.path.join(os.getcwd(), 'tree.tree'))
# for pre, fill, node in anytree.RenderTree(treeModel.tree):
#     print("{}{}".format(pre, node.name))


