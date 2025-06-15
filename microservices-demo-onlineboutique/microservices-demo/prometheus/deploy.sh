#!/bin/bash

# Prometheus监控系统自动部署脚本
# 适用于Online Boutique微服务系统

set -e

echo "🚀 开始部署Prometheus监控系统..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查kubectl是否可用
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl命令未找到，请先安装kubectl"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        print_error "无法连接到Kubernetes集群，请检查kubeconfig配置"
        exit 1
    fi
    
    print_success "Kubernetes集群连接正常"
}

# 检查必要文件是否存在
check_files() {
    local files=(
        "prometheus-rbac.yaml"
        "prometheus-deployment.yaml"
        "grafana-deployment.yaml"
    )
    
    for file in "${files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "文件 $file 不存在"
            exit 1
        fi
    done
    
    print_success "所有必要文件检查完成"
}

# 部署RBAC权限
deploy_rbac() {
    print_status "部署Prometheus RBAC权限..."
    kubectl apply -f prometheus-rbac.yaml
    print_success "RBAC权限部署完成"
}

# 部署Prometheus
deploy_prometheus() {
    print_status "部署Prometheus服务..."
    kubectl apply -f prometheus-deployment.yaml
    
    # 等待Prometheus Pod就绪
    print_status "等待Prometheus Pod启动..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=300s
    print_success "Prometheus部署完成"
}

# 部署Grafana
deploy_grafana() {
    print_status "部署Grafana服务..."
    kubectl apply -f grafana-deployment.yaml
    
    # 等待Grafana Pod就绪
    print_status "等待Grafana Pod启动..."
    kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=300s
    print_success "Grafana部署完成"
}

# 部署ServiceMonitor (可选)
deploy_servicemonitor() {
    if [[ -f "servicemonitor.yaml" ]]; then
        print_status "部署ServiceMonitor..."
        kubectl apply -f servicemonitor.yaml
        print_success "ServiceMonitor部署完成"
    else
        print_warning "servicemonitor.yaml文件不存在，跳过ServiceMonitor部署"
    fi
}

# 为Online Boutique服务添加监控标签
add_service_labels() {
    print_status "为Online Boutique服务添加监控标签..."
    
    local services=(
        "frontend"
        "cartservice"
        "productcatalogservice"
        "currencyservice"
        "paymentservice"
        "shippingservice"
        "emailservice"
        "checkoutservice"
        "recommendationservice"
        "adservice"
        "loadgenerator"
    )
    
    for service in "${services[@]}"; do
        if kubectl get service "$service" &> /dev/null; then
            kubectl label service "$service" app="$service" --overwrite
            print_status "已为服务 $service 添加标签"
        else
            print_warning "服务 $service 不存在，跳过标签添加"
        fi
    done
    
    print_success "服务标签添加完成"
}

# 获取访问信息
get_access_info() {
    print_status "获取访问信息..."
    
    # 获取Minikube IP (如果使用Minikube)
    if command -v minikube &> /dev/null && minikube status &> /dev/null; then
        MINIKUBE_IP=$(minikube ip)
        echo ""
        echo "=== 🌐 访问信息 ==="
        echo "Prometheus: http://$MINIKUBE_IP:30090"
        echo "Grafana:    http://$MINIKUBE_IP:30030"
        echo "  用户名: admin"
        echo "  密码:   admin123"
    else
        echo ""
        echo "=== 🌐 访问信息 ==="
        echo "如果使用NodePort访问，请获取节点IP："
        echo "kubectl get nodes -o wide"
        echo ""
        echo "然后访问："
        echo "Prometheus: http://<NODE_IP>:30090"
        echo "Grafana:    http://<NODE_IP>:30030"
        echo "  用户名: admin"
        echo "  密码:   admin123"
    fi
    
    echo ""
    echo "=== 📊 端口转发访问 (可选) ==="
    echo "Prometheus: kubectl port-forward -n monitoring svc/prometheus-service 9090:9090"
    echo "Grafana:    kubectl port-forward -n monitoring svc/grafana-service 3000:3000"
}

# 检查部署状态
check_deployment_status() {
    print_status "检查部署状态..."
    
    echo ""
    echo "=== 📋 Pod状态 ==="
    kubectl get pods -n monitoring
    
    echo ""
    echo "=== 🔗 服务状态 ==="
    kubectl get services -n monitoring
    
    echo ""
    echo "=== 🎯 Prometheus目标检查 ==="
    echo "访问 Prometheus Web UI 并检查 /targets 页面"
    echo "确认所有目标服务都被正确发现"
}

# 主函数
main() {
    echo "=================================================="
    echo "🔍 Prometheus + Grafana 监控系统部署脚本"
    echo "适用于 Online Boutique 微服务系统"
    echo "=================================================="
    
    # 执行部署步骤
    check_kubectl
    check_files
    deploy_rbac
    deploy_prometheus
    deploy_grafana
    deploy_servicemonitor
    add_service_labels
    
    # 等待所有服务完全启动
    print_status "等待所有服务完全启动..."
    sleep 10
    
    # 显示部署结果
    check_deployment_status
    get_access_info
    
    echo ""
    print_success "🎉 Prometheus监控系统部署完成！"
    echo ""
    echo "=== 📚 下一步操作 ==="
    echo "1. 访问Prometheus检查监控目标"
    echo "2. 登录Grafana配置仪表板"
    echo "3. 导入推荐的仪表板模板"
    echo "4. 设置告警规则 (可选)"
    echo ""
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 