from src.values.types.number import Number
from src.values.value import Value
from src.error.message.rt import RTError

class List(Value):
  def __init__(self, elements, elem_annotation=None, max_size=None):
    super().__init__()
    self.elements = elements
    self.elem_annotation = elem_annotation
    self.max_size = max_size

  def _check_elem(self, value):
    if self.elem_annotation is None:
      return None
    from src.run.typecheck import check_type
    pos_s = value.pos_start if value.pos_start else self.pos_start
    pos_e = value.pos_end if value.pos_end else self.pos_end
    return check_type(value, self.elem_annotation, self.context, pos_s, pos_e)

  def _check_size(self, extra=1):
    if self.max_size is None:
      return None
    if len(self.elements) + extra > self.max_size:
      return RTError(
        self.pos_start, self.pos_end,
        f"Array exceeds maximum size of {self.max_size} "
        f"(current: {len(self.elements)}, adding: {extra})",
        self.context
      )
    return None

  def added_to(self, other):
    err = self._check_size(1)
    if err: return None, err
    err = self._check_elem(other)
    if err: return None, err
    new_list = self.copy()
    new_list.elements.append(other)
    return new_list, None

  def subbed_by(self, other):
    if isinstance(other, Number):
      new_list = self.copy()
      try:
        new_list.elements.pop(other.value)
        return new_list, None
      except:
        return None, RTError(
          other.pos_start, other.pos_end,
          f'Index {other.value} is out of range for array of length {len(self.elements)}',
          self.context
        )
    else:
      return None, Value.illegal_operation(self, other, op='-')

  def multed_by(self, other):
    if isinstance(other, List):
      err = self._check_size(len(other.elements))
      if err: return None, err
      for elem in other.elements:
        err = self._check_elem(elem)
        if err: return None, err
      new_list = self.copy()
      new_list.elements.extend(other.elements)
      return new_list, None
    else:
      return None, Value.illegal_operation(self, other, op='*')

  def dived_by(self, other):
    if isinstance(other, Number):
      try:
        return self.elements[other.value], None
      except:
        return None, RTError(
          other.pos_start, other.pos_end,
          f'Index {other.value} is out of range for array of length {len(self.elements)}',
          self.context
        )
    else:
      return None, Value.illegal_operation(self, other, op='/')

  def copy(self):
    copy = List(self.elements, self.elem_annotation, self.max_size)
    copy.set_pos(self.pos_start, self.pos_end)
    copy.set_context(self.context)
    return copy

  def __str__(self):
    return ", ".join([str(x) for x in self.elements])

  def __repr__(self):
    return f'[{", ".join([str(x) for x in self.elements])}]'