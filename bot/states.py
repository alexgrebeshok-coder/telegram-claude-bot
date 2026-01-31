from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    """Состояния при создании новой задачи"""
    waiting_prompt = State()


class ManagementStates(StatesGroup):
    """Состояния для управления проектами"""
    viewing_tasks = State()
