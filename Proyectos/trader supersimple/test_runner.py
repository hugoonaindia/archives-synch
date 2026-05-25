"""
Test runner script for trader supersimple project
Generates test coverage and metrics reports
"""

import pytest
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import coverage

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_tests():
    """Run all tests and generate reports"""
    print("🚀 Iniciando ejecución de tests para trader supersimple...")
    
    # Create reports directory
    reports_dir = project_root / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Timestamp for report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize coverage
    cov = coverage.Coverage(
        source=[str(project_root / "src")],
        omit=["*/tests/*", "*/venv/*", "*/.venv/*"]
    )
    cov.start()
    
    # Run tests with pytest
    test_start_time = time.time()
    
    # Run pytest with detailed output
    result = pytest.main([
        str(project_root / "tests"),
        "-v",
        "--tb=short",
        "--color=yes",
        f"--junit-xml={reports_dir}/test_results_{timestamp}.xml"
    ])
    
    test_end_time = time.time()
    test_duration = test_end_time - test_start_time
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    # Generate coverage HTML report
    cov_html_dir = reports_dir / f"coverage_{timestamp}"
    cov.html_report(directory=str(cov_html_dir))
    
    # Generate coverage JSON report
    cov_data = cov.get_data()
    
    # Calculate coverage metrics
    total_lines = 0
    covered_lines = 0
    
    for filename, file_lines in cov_data.items():
        if filename.startswith(str(project_root / "src")):
            total_lines += len(file_lines)
            covered_lines += len([line for line, hit in file_lines.items() if hit])
    
    coverage_percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
    
    # Generate metrics report
    metrics = {
        "timestamp": timestamp,
        "test_duration_seconds": round(test_duration, 2),
        "exit_code": result,
        "total_files_analyzed": len([f for f in cov_data.keys() if f.startswith(str(project_root / "src"))]),
        "total_lines": total_lines,
        "covered_lines": covered_lines,
        "coverage_percentage": round(coverage_percentage, 2),
        "test_status": "PASSED" if result == 0 else "FAILED",
        "coverage_trend": "IMPROVED" if coverage_percentage > 0 else "NEW_COVERAGE"
    }
    
    # Save metrics report
    with open(reports_dir / f"metrics_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    # Generate summary report
    generate_summary_report(metrics, reports_dir, timestamp)
    
    print(f"\n📊 Informe de tests generado en: {reports_dir}")
    print(f"🎯 Porcentaje de cobertura: {coverage_percentage:.1f}%")
    print(f"⏱️ Tiempo de ejecución: {test_duration:.2f}s")
    print(f"✅ Estado: {'PASSED' if result == 0 else 'FAILED'}")
    
    return result, coverage_percentage

def generate_summary_report(metrics, reports_dir, timestamp):
    """Generate a human-readable summary report"""
    
    summary_content = f"""
# Reporte de Tests - Trader Supersimple

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**ID del Reporte:** {timestamp}

## Resumen Ejecución

- **Estado de Tests:** {metrics['test_status']}
- **Código de Salida:** {metrics['exit_code']}
- **Tiempo de Ejecución:** {metrics['test_duration_seconds']}s
- **Archivos Analizados:** {metrics['total_files_analyzed']}

## Métricas de Cobertura

- **Líneas Totales:** {metrics['total_lines']}
- **Líneas Cubiertas:** {metrics['covered_lines']}
- **Porcentaje de Cobertura:** {metrics['coverage_percentage']}%
- **Tendencia:** {metrics['coverage_trend']}

## Archivos Generados

- **Resultados XML:** test_results_{timestamp}.xml
- **Métricas JSON:** metrics_{timestamp}.json
- **Reporte HTML:** coverage_{timestamp}/index.html

## Próximos Pasos

{get_next_steps(metrics)}

---
*Generado automáticamente por el test runner*
"""
    
    with open(reports_dir / f"summary_{timestamp}.md", "w", encoding="utf-8") as f:
        f.write(summary_content)

def get_next_steps(metrics):
    """Get next steps based on metrics"""
    if metrics['coverage_percentage'] == 0:
        return """
🔥 **Prioridad Alta:**
- Implementar tests unitarios para todos los módulos principales
- Crear fixtures para datos de prueba comunes
- Asegurar cobertura del 80% en módulos críticos
"""
    elif metrics['coverage_percentage'] < 50:
        return """
📈 **Mejora Requerida:**
- Aumentar cobertura a al menos 70%
- Agregar tests para casos de borde y errores
- Implementar tests de integración
"""
    elif metrics['coverage_percentage'] < 80:
        return """
✅ **Buen Progreso:**
- Buscar aumentar cobertura al 90%
- Agregar pruebas de rendimiento
- Implementar TDD para nuevas funcionalidades
"""
    else:
        return """
🎯 **Excelente Cobertura:**
- Mantener cobertura >90%
- Implementar pruebas de regresión
- Considerar pruebas de extremo a extremo
"""

def check_dependencies():
    """Check if all required dependencies are available"""
    required_packages = [
        'pytest',
        'coverage',
        'pytest-cov'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Paquetes faltantes: {', '.join(missing_packages)}")
        print("Instalar con: pip install pytest coverage pytest-cov")
        return False
    
    return True

def main():
    """Main function"""
    print("🔍 Verificando dependencias...")
    
    if not check_dependencies():
        sys.exit(1)
    
    try:
        exit_code, coverage_percentage = run_tests()
        
        # Exit with appropriate code
        if exit_code != 0:
            print("\n❌ Algunos tests fallaron")
            sys.exit(1)
        elif coverage_percentage == 0:
            print("\n⚠️  Tests pasaron pero no hay cobertura de tests")
            sys.exit(0)
        else:
            print(f"\n✅ Todos los tests pasaron con {coverage_percentage:.1f}% cobertura")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()