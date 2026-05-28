"""
Base UI components with proper separation of responsibilities.
Implements the NiceGUI layout foundation.
"""

from typing import Dict, Any, Optional, List
import nicegui
from nicegui import ui
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ComponentConfig:
    """Base configuration for UI components"""
    title: str
    description: str = ""
    width: str = "auto"
    height: str = "auto"
    classes: List[str] = None
    
    def __post_init__(self):
        if self.classes is None:
            self.classes = []


class BaseComponent(ABC):
    """Base class for all UI components"""
    
    def __init__(self, config: ComponentConfig):
        self.config = config
        self._element: Optional[ui.element] = None
        self._children: Dict[str, BaseComponent] = {}
    
    @abstractmethod
    def render(self) -> ui.element:
        """Render the component - must be implemented by subclasses"""
        pass
    
    def add_child(self, name: str, child: 'BaseComponent'):
        """Add a child component"""
        self._children[name] = child
        return child
    
    def get_child(self, name: str) -> Optional['BaseComponent']:
        """Get a child component by name"""
        return self._children.get(name)
    
    def remove_child(self, name: str):
        """Remove a child component"""
        if name in self._children:
            del self._children[name]
    
    def clear_children(self):
        """Clear all child components"""
        self._children.clear()
    
    def apply_config(self, element: ui.element):
        """Apply configuration to the element"""
        if self.config.classes:
            element.classes(*self.config.classes)
        
        # Apply width and height
        if self.config.width != "auto":
            element.style(f"width: {self.config.width}")
        if self.config.height != "auto":
            element.style(f"height: {self.config.height}")


class HeaderComponent(BaseComponent):
    """Header component with collapsible sidebar"""
    
    def __init__(self, config: ComponentConfig):
        super().__init__(config)
        self.sidebar_visible = True
        self._sidebar: Optional[ui.left_drawer] = None
        self._main_content: Optional[ui.element] = None
    
    def render(self) -> ui.element:
        """Render the header with sidebar"""
        with ui.header().classes('bg-white shadow-lg q-pa-md') as header:
            # Main title
            ui.label(self.config.title).classes('text-xl font-bold')
            
            # Sidebar toggle button
            with ui.row().classes('items-center gap-4'):
                ui.button(
                    '☰',
                    on_click=self._toggle_sidebar,
                    classes='text-gray-600 hover:text-gray-800'
                ).tooltip('Toggle Sidebar')
                
                # Navigation buttons
                ui.button('Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
                ui.button('Config', on_click=lambda: ui.navigate.to('/config'))
                ui.button('Analysis', on_click=lambda: ui.navigate.to('/analysis'))
        
        return header
    
    def _toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self._sidebar:
            self._sidebar.toggle()
    
    def set_sidebar(self, sidebar: ui.left_drawer):
        """Set the sidebar reference"""
        self._sidebar = sidebar
    
    def set_main_content(self, content: ui.element):
        """Set the main content reference"""
        self._main_content = content


class SidebarComponent(BaseComponent):
    """Collapsible sidebar component"""
    
    def __init__(self, config: ComponentConfig):
        super().__init__(config)
        self._header: Optional[HeaderComponent] = None
    
    def render(self) -> ui.element:
        """Render the sidebar"""
        with ui.left_drawer().classes('bg-gray-50 w-64') as sidebar:
            # Sidebar header
            with ui.column().classes('p-4 border-b'):
                ui.label('Navigation').classes('text-lg font-semibold')
            
            # Navigation menu
            with ui.column().classes('p-2 space-y-1'):
                self._create_menu_item('Dashboard', '/dashboard', '📊')
                self._create_menu_item('Configuration', '/config', '⚙️')
                self._create_menu_item('Data Analysis', '/analysis', '📈')
                self._create_menu_item('Users', '/users', '👥')
                self._create_menu_item('Settings', '/settings', '🔧')
            
            # User info section
            with ui.column().classes('p-4 border-t mt-4'):
                ui.label('User: Admin').classes('text-sm font-medium')
                ui.button('Logout', on_click=self._logout).classes('w-full mt-2')
        
        return sidebar
    
    def _create_menu_item(self, label: str, route: str, icon: str = ''):
        """Create a menu item"""
        with ui.button(label, on_click=lambda: ui.navigate.to(route)).classes(
            'w-full justify-start p-3 rounded-lg hover:bg-gray-200 transition-colors'
        ):
            if icon:
                ui.label(icon).classes('mr-2')
    
    def _logout(self):
        """Handle logout"""
        ui.notify('Logout functionality not implemented yet', color='warning')
    
    def set_header(self, header: HeaderComponent):
        """Set the header reference"""
        self._header = header
        header.set_sidebar(self)


class CardComponent(BaseComponent):
    """Card component for displaying content"""
    
    def render(self) -> ui.element:
        """Render a card"""
        with ui.card().classes('shadow-lg rounded-lg') as card:
            ui.label(self.config.title).classes('text-lg font-semibold mb-2')
            
            if self.config.description:
                ui.label(self.config.description).classes('text-gray-600 text-sm')
            
            # Content area for children
            with ui.column().classes('mt-4 space-y-2'):
                for child in self._children.values():
                    child.render()
        
        return card


class DataTableComponent(BaseComponent):
    """Data table component for displaying tabular data"""
    
    def __init__(self, config: ComponentConfig, columns: List[str], data: List[Dict[str, Any]]):
        super().__init__(config)
        self.columns = columns
        self.data = data
    
    def render(self) -> ui.element:
        """Render a data table"""
        with ui.card().classes('shadow-lg'):
            ui.label(self.config.title).classes('text-lg font-semibold mb-4')
            
            # Create table
            with ui.table(columns=self.columns).classes('w-full'):
                for row in self.data:
                    ui.row([str(row.get(col, '')) for col in self.columns])
        
        return ui.element('div')


class FormComponent(BaseComponent):
    """Form component for user input"""
    
    def __init__(self, config: ComponentConfig, fields: List[Dict[str, Any]]):
        super().__init__(config)
        self.fields = fields
        self._form_data: Dict[str, Any] = {}
    
    def render(self) -> ui.element:
        """Render a form"""
        with ui.card().classes('shadow-lg p-6'):
            ui.label(self.config.title).classes('text-lg font-semibold mb-4')
            
            # Create form fields
            with ui.column().classes('space-y-4'):
                for field in self.fields:
                    self._create_field(field)
                
                # Form actions
                with ui.row().classes('justify-end gap-2 mt-6'):
                    ui.button('Cancel', on_click=self._cancel).classes('px-4 py-2 bg-gray-200 rounded')
                    ui.button('Submit', on_click=self._submit).classes('px-4 py-2 bg-blue-500 text-white rounded')
        
        return ui.element('div')
    
    def _create_field(self, field: Dict[str, Any]):
        """Create a form field"""
        field_type = field.get('type', 'text')
        field_name = field.get('name', '')
        field_label = field.get('label', field_name)
        field_required = field.get('required', False)
        
        with ui.row().classes('items-center'):
            ui.label(field_label).classes('w-32 font-medium')
            
            if field_type == 'text':
                input_element = ui.input(label=field_label).classes('w-full')
            elif field_type == 'number':
                input_element = ui.number(label=field_label).classes('w-full')
            elif field_type == 'select':
                options = field.get('options', [])
                input_element = ui.select(options, label=field_label).classes('w-full')
            elif field_type == 'textarea':
                input_element = ui.textarea(label=field_label).classes('w-full')
            else:
                input_element = ui.input(label=field_label).classes('w-full')
            
            if field_required:
                input_element.props('required')
            
            # Store reference for data collection
            self._form_data[field_name] = input_element
    
    def _submit(self):
        """Handle form submission"""
        # Collect form data
        data = {}
        for field_name, input_element in self._form_data.items():
            data[field_name] = input_element.value
        
        ui.notify('Form submitted successfully!', color='positive')
        print(f"Form data: {data}")
    
    def _cancel(self):
        """Handle form cancellation"""
        ui.notify('Form cancelled', color='warning')


class LayoutFactory:
    """Factory for creating common layouts"""
    
    @staticmethod
    def create_main_layout(title: str = "Clinical/Trading Automation Engine") -> Dict[str, BaseComponent]:
        """Create the main application layout"""
        header_config = ComponentConfig(
            title=title,
            classes="bg-white shadow-lg"
        )
        
        sidebar_config = ComponentConfig(
            title="Navigation",
            classes="bg-gray-50"
        )
        
        header = HeaderComponent(header_config)
        sidebar = SidebarComponent(sidebar_config)
        
        # Connect header and sidebar
        sidebar.set_header(header)
        
        return {
            'header': header,
            'sidebar': sidebar
        }
    
    @staticmethod
    def create_dashboard_card(title: str, value: str, color: str = "blue") -> CardComponent:
        """Create a dashboard card"""
        config = ComponentConfig(
            title=title,
            classes=f"bg-{color}-50 border border-{color}-200"
        )
        
        card = CardComponent(config)
        with ui.column().classes('text-center'):
            ui.label(value).classes(f'text-3xl font-bold text-{color}-600')
            ui.label('Status').classes('text-sm text-gray-500')
        
        return card