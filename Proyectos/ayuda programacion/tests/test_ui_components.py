"""
Test cases for UI components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.base import (
    ComponentConfig,
    BaseComponent,
    HeaderComponent,
    SidebarComponent,
    CardComponent,
    DataTableComponent,
    FormComponent,
    LayoutFactory
)


class TestComponentConfig:
    """Test cases for ComponentConfig class"""
    
    def test_component_config_creation(self):
        """Test component configuration creation"""
        config = ComponentConfig(
            title="Test Component",
            description="Test description",
            width="300px",
            height="200px",
            classes=["test-class", "another-class"]
        )
        
        assert config.title == "Test Component"
        assert config.description == "Test description"
        assert config.width == "300px"
        assert config.height == "200px"
        assert config.classes == ["test-class", "another-class"]
    
    def test_component_config_defaults(self):
        """Test component configuration defaults"""
        config = ComponentConfig(title="Test")
        
        assert config.title == "Test"
        assert config.description == ""
        assert config.width == "auto"
        assert config.height == "auto"
        assert config.classes == []


class TestBaseComponent:
    """Test cases for BaseComponent class"""
    
    def test_base_component_creation(self):
        """Test base component creation"""
        config = ComponentConfig(title="Test Component")
        
        # Create a concrete implementation for testing
        class TestConcreteComponent(BaseComponent):
            def render(self):
                return Mock()  # Mock UI element
        
        component = TestConcreteComponent(config)
        
        assert component.config == config
        assert component._element is None
        assert component._children == {}
    
    def test_add_child(self):
        """Test adding child components"""
        config = ComponentConfig(title="Parent")
        
        class TestConcreteComponent(BaseComponent):
            def render(self):
                return Mock()  # Mock UI element
        
        parent = TestConcreteComponent(config)
        
        child_config = ComponentConfig(title="Child")
        child = TestConcreteComponent(child_config)
        
        parent.add_child("test_child", child)
        
        assert "test_child" in parent._children
        assert parent._children["test_child"] == child
    
    def test_get_child(self):
        """Test getting child components"""
        config = ComponentConfig(title="Parent")
        
        class TestConcreteComponent(BaseComponent):
            def render(self):
                return Mock()  # Mock UI element
        
        parent = TestConcreteComponent(config)
        
        child_config = ComponentConfig(title="Child")
        child = TestConcreteComponent(child_config)
        
        parent.add_child("test_child", child)
        
        retrieved_child = parent.get_child("test_child")
        assert retrieved_child == child
        
        nonexistent_child = parent.get_child("nonexistent")
        assert nonexistent_child is None
    
    def test_remove_child(self):
        """Test removing child components"""
        config = ComponentConfig(title="Parent")
        
        class TestConcreteComponent(BaseComponent):
            def render(self):
                return Mock()  # Mock UI element
        
        parent = TestConcreteComponent(config)
        
        child_config = ComponentConfig(title="Child")
        child = TestConcreteComponent(child_config)
        
        parent.add_child("test_child", child)
        assert "test_child" in parent._children
        
        parent.remove_child("test_child")
        assert "test_child" not in parent._children
    
    def test_clear_children(self):
        """Test clearing all child components"""
        config = ComponentConfig(title="Parent")
        
        class TestConcreteComponent(BaseComponent):
            def render(self):
                return Mock()  # Mock UI element
        
        parent = TestConcreteComponent(config)
        
        # Add multiple children
        for i in range(3):
            child_config = ComponentConfig(title=f"Child {i}")
            child = TestConcreteComponent(child_config)
            parent.add_child(f"child_{i}", child)
        
        assert len(parent._children) == 3
        
        parent.clear_children()
        assert len(parent._children) == 0


class TestHeaderComponent:
    """Test cases for HeaderComponent class"""
    
    def test_header_component_creation(self):
        """Test header component creation"""
        config = ComponentConfig(title="Test Header")
        header = HeaderComponent(config)
        
        assert header.config == config
        assert header._sidebar is None
        assert header._main_content is None
        assert header.sidebar_visible is True
    
    def test_toggle_sidebar(self):
        """Test sidebar toggle functionality"""
        config = ComponentConfig(title="Test Header")
        header = HeaderComponent(config)
        
        # Mock sidebar
        mock_sidebar = Mock()
        mock_sidebar.toggle = Mock()
        header._sidebar = mock_sidebar
        
        header._toggle_sidebar()
        
        mock_sidebar.toggle.assert_called_once()


class TestSidebarComponent:
    """Test cases for SidebarComponent class"""
    
    def test_sidebar_component_creation(self):
        """Test sidebar component creation"""
        config = ComponentConfig(title="Test Sidebar")
        sidebar = SidebarComponent(config)
        
        assert sidebar.config == config
        assert sidebar._header is None
    
    def test_logout_handler(self):
        """Test logout handler"""
        config = ComponentConfig(title="Test Sidebar")
        sidebar = SidebarComponent(config)
        
        # Mock UI notify
        with patch('src.ui.components.base.ui') as mock_ui:
            sidebar._logout()
            mock_ui.notify.assert_called_once_with(
                'Logout functionality not implemented yet', 
                color='warning'
            )


class TestCardComponent:
    """Test cases for CardComponent class"""
    
    def test_card_component_creation(self):
        """Test card component creation"""
        config = ComponentConfig(title="Test Card")
        card = CardComponent(config)
        
        assert card.config == config


class TestDataTableComponent:
    """Test cases for DataTableComponent class"""
    
    def test_data_table_component_creation(self):
        """Test data table component creation"""
        config = ComponentConfig(title="Test Table")
        columns = ["id", "name", "email"]
        data = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"}
        ]
        
        table = DataTableComponent(config, columns, data)
        
        assert table.config == config
        assert table.columns == columns
        assert table.data == data


class TestFormComponent:
    """Test cases for FormComponent class"""
    
    def test_form_component_creation(self):
        """Test form component creation"""
        config = ComponentConfig(title="Test Form")
        fields = [
            {"name": "username", "label": "Username", "type": "text", "required": True},
            {"name": "email", "label": "Email", "type": "email", "required": False},
            {"name": "age", "label": "Age", "type": "number", "required": True}
        ]
        
        form = FormComponent(config, fields)
        
        assert form.config == config
        assert form.fields == fields
        assert form._form_data == {}
    
    def test_create_field_text(self):
        """Test creating text input field"""
        config = ComponentConfig(title="Test Form")
        fields = [{"name": "username", "label": "Username", "type": "text"}]
        
        form = FormComponent(config, fields)
        
        # Mock ui.row and ui.input
        with patch('src.ui.components.base.ui') as mock_ui:
            row_mock = Mock()
            input_mock = Mock()
            mock_ui.row.return_value.__enter__.return_value = row_mock
            mock_ui.input.return_value = input_mock
            
            form._create_field(fields[0])
            
            mock_ui.row.assert_called_once()
            mock_ui.input.assert_called_once_with(label="Username")
    
    def test_create_field_number(self):
        """Test creating number input field"""
        config = ComponentConfig(title="Test Form")
        fields = [{"name": "age", "label": "Age", "type": "number"}]
        
        form = FormComponent(config, fields)
        
        with patch('src.ui.components.base.ui') as mock_ui:
            row_mock = Mock()
            number_mock = Mock()
            mock_ui.row.return_value.__enter__.return_value = row_mock
            mock_ui.number.return_value = number_mock
            
            form._create_field(fields[0])
            
            mock_ui.number.assert_called_once_with(label="Age")
    
    def test_create_field_select(self):
        """Test creating select field"""
        config = ComponentConfig(title="Test Form")
        fields = [
            {
                "name": "country", 
                "label": "Country", 
                "type": "select", 
                "options": ["US", "CA", "MX"]
            }
        ]
        
        form = FormComponent(config, fields)
        
        with patch('src.ui.components.base.ui') as mock_ui:
            row_mock = Mock()
            select_mock = Mock()
            mock_ui.row.return_value.__enter__.return_value = row_mock
            mock_ui.select.return_value = select_mock
            
            form._create_field(fields[0])
            
            mock_ui.select.assert_called_once_with(["US", "CA", "MX"], label="Country")


class TestLayoutFactory:
    """Test cases for LayoutFactory class"""
    
    def test_create_main_layout(self):
        """Test creating main layout"""
        layout = LayoutFactory.create_main_layout("Test App")
        
        assert "header" in layout
        assert "sidebar" in layout
        assert isinstance(layout["header"], HeaderComponent)
        assert isinstance(layout["sidebar"], SidebarComponent)
        
        # Check that header and sidebar are connected
        assert layout["sidebar"]._header == layout["header"]
        assert layout["header"]._sidebar == layout["sidebar"]
    
    def test_create_dashboard_card(self):
        """Test creating dashboard card"""
        card = LayoutFactory.create_dashboard_card("Users", "42", "blue")
        
        assert isinstance(card, CardComponent)
        assert card.config.title == "Users"
    
    def test_create_dashboard_card_different_colors(self):
        """Test creating dashboard cards with different colors"""
        colors = ["red", "green", "yellow", "purple"]
        
        for color in colors:
            card = LayoutFactory.create_dashboard_card(f"Test {color}", "10", color)
            assert isinstance(card, CardComponent)
            assert card.config.title == f"Test {color}"