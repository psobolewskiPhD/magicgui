# -*- coding: utf-8 -*-
"""Widgets and type-to-widget conversion for the Qt backend."""

import sys
from contextlib import contextmanager
from enum import Enum, EnumMeta
from typing import Any, Callable, Dict, Iterable, NamedTuple, Optional, Type, Tuple

from qtpy.QtCore import Signal, SignalInstance
from qtpy.QtWidgets import (
    QAbstractButton,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@contextmanager
def event_loop():
    """Start a Qt event loop in which to run the application."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield
    app.exec_()


WidgetType = QWidget
ButtonType = QPushButton
SignalType = Signal


class GetSetOnChange(NamedTuple):
    """Named tuple for a (getter, setter, onchange) tuple."""

    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    onchange: SignalInstance


class Layout(Enum):
    """QLayout options."""

    vertical = QVBoxLayout
    horizontal = QHBoxLayout
    grid = QGridLayout
    form = QFormLayout

    @classmethod
    def _missing_(cls, value: object) -> Any:
        options = cls._member_names_
        raise ValueError(f"'{value}' is not a valid Layout. Options include: {options}")


class QDataComboBox(QComboBox):
    """A CombBox subclass that emits data objects when the index changes."""

    currentDataChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.currentIndexChanged.connect(self._emit_data)

    def _emit_data(self, index: int) -> None:
        data = self.itemData(index)
        if data is not None:
            self.currentDataChanged.emit(data)


def type2widget(type_: type) -> Type[WidgetType]:
    """Convert an python type to Qt widget.

    Parameters
    ----------
    type_ : type
        The argument type.

    Returns
    -------
    WidgetType: Type[WidgetType]
        A WidgetType Class that can be used for arg_type ``type_``.
    """
    simple: Dict[type, Type[WidgetType]] = {
        bool: QCheckBox,
        int: QSpinBox,
        float: QDoubleSpinBox,
        str: QLineEdit,
        type(None): QLineEdit,
    }
    if type_ in simple:
        return simple[type_]
    elif isinstance(type_, EnumMeta):
        return QDataComboBox


def getter_setter_onchange(widget: WidgetType) -> GetSetOnChange:
    """Return a GetSetOnChange tuple for widgets of class ``WidgetType``.

    Parameters
    ----------
    widget : WidgetType
        A widget class in Qt

    Returns
    -------
    GetSetOnChange : tuple
        (getter, setter, onchange) functions for this widget class.

    Raises
    ------
    ValueError
        If the widget class is unrecognzed.
    """
    if isinstance(widget, QComboBox):

        def getter():
            return widget.itemData(widget.currentIndex())

        onchange = (
            widget.currentDataChanged
            if isinstance(widget, QDataComboBox)
            else widget.currentIndexChanged
        )
        return GetSetOnChange(getter, widget.setCurrentIndex, onchange)
    elif isinstance(widget, QStatusBar):
        return GetSetOnChange(
            widget.currentMessage, widget.showMessage, widget.messageChanged
        )
    elif isinstance(widget, QLineEdit):
        return GetSetOnChange(widget.text, widget.setText, widget.textChanged)
    elif isinstance(widget, (QAbstractButton, QGroupBox)):
        return GetSetOnChange(widget.isChecked, widget.setChecked, widget.toggled)
    elif isinstance(widget, QDateTimeEdit):
        return GetSetOnChange(
            widget.dateTime, widget.setDateTime, widget.dateTimeChanged
        )
    elif isinstance(widget, (QAbstractSpinBox, QAbstractSlider)):
        return GetSetOnChange(widget.value, widget.setValue, widget.valueChanged)
    elif isinstance(widget, QTabWidget):
        return GetSetOnChange(
            widget.currentIndex, widget.setCurrentIndex, widget.currentChanged
        )
    elif isinstance(widget, QSplitter):
        return GetSetOnChange(widget.sizes, widget.setSizes, widget.splitterMoved)
    raise ValueError(f"Unrecognized widget Type: {widget}")


def set_categorical_choices(widget: WidgetType, choices: Iterable[Tuple[str, Any]]):
    """Set current items in categorical type ``widget`` to ``choices``."""
    names = [x[0] for x in choices]
    for i in range(widget.count()):
        if widget.itemText(i) not in names:
            widget.removeItem(i)
    for name, data in choices:
        if widget.findText(name) == -1:
            widget.addItem(name, data)


def get_categorical_widget():
    """Get the categorical widget type for Qt."""
    return QDataComboBox


def is_categorical(widget: WidgetType):
    """Return True if ``widget`` is a categorical widget."""
    return isinstance(widget, QComboBox)


def get_categorical_index(widget: WidgetType, value: Any):
    """Find the index of ``value`` in categorical-type ``widget``."""
    return next(i for i in range(widget.count()) if widget.itemData(i) == value)


def make_widget(
    WidgetType: Type[WidgetType],
    name: Optional[str] = None,
    parent: WidgetType = None,
    **kwargs,
) -> WidgetType:
    """Instantiate a new widget of type ``WidgetType``.

    This function allows for any ``widget.set<AttrName>()`` setter to be called by
    providing the corresponding ``attrName: value`` as a key/value in pair in
    ``**kwargs``.

    Parameters
    ----------
    WidgetType : Type[WidgetType]
        The widget class to create.
    name : str, optional
        Name of the widget.  If provided, will be set as ObjectName. by default None
    parent : WidgetType, optional
        Optional parent widget instance, by default None
    **kwargs : dict
        For each ``key`` in ``kwargs``, if there is a setter method on the instantiated
        widget called ``set<key>``, it will called with ``kwargs[key]``.  Note, the
        first letter of ``key`` needn't be capitalized.

    Returns
    -------
    widget : WidgetType
        The newly instantiated widget
    """
    widget = WidgetType(parent=parent)
    if name:
        widget.setObjectName(name)
    for key, val in kwargs.items():
        setter = getattr(widget, f"set{key[0].upper() + key[1:]}", None)
        if setter:
            setter(val)

    return widget
