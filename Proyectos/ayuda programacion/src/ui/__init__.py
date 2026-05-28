"""
UI components package for user interface elements.
"""

try:
    # Try to import from local directory first
    import sys
    from pathlib import Path
    
    # Add the components directory to path
    components_dir = Path(__file__).parent / "components"
    if components_dir.exists():
        sys.path.insert(0, str(components_dir))
    
    from .base import (
        BaseComponent, 
        HeaderComponent, 
        SidebarComponent, 
        CardComponent,
        DataTableComponent,
        FormComponent,
        LayoutFactory
    )
except ImportError as e:
    # Log the import error but don't fail the package loading
    print(f"Warning: UI components could not be imported: {e}")
    BaseComponent = None
    HeaderComponent = None
    SidebarComponent = None
    CardComponent = None
    DataTableComponent = None
    FormComponent = None
    LayoutFactory = None

__all__ = [
    'BaseComponent',
    'HeaderComponent', 
    'SidebarComponent',
    'CardComponent',
    'DataTableComponent',
    'FormComponent',
    'LayoutFactory'
]