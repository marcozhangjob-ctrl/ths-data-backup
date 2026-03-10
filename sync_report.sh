#!/bin/bash

# sync_report.sh - 同步报告和备份脚本
# 用于生成同步状态报告和备份同花顺交易数据

# 切换到工作目录
cd /home/openclaw/.openclaw/workspace

# ============================================
# 模式选择
# ============================================
MODE="${1:-report}"

case "$MODE" in
    backup)
        # ============================================
        # 备份模式：备份同花顺交易数据
        # ============================================
        SOURCE_DIR="/home/openclaw/.openclaw/workspace/实时监控！"
        
        echo "========================================="
        echo "  同花顺交易数据备份 - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================="
        echo ""
        
        # 检查 GitHub CLI
        echo "🔐 检查 GitHub 登录状态..."
        if ! gh auth status > /dev/null 2>&1; then
            echo "❌ GitHub 未登录，请先运行: gh auth login"
            exit 1
        fi
        echo "✅ GitHub 已登录"
        echo ""
        
        # 创建备份目录
        BACKUP_DIR="$SOURCE_DIR/backup"
        mkdir -p "$BACKUP_DIR"
        
        # 备份数据文件
        echo "📦 正在备份数据文件..."
        if [ -f "$SOURCE_DIR/portfolio_data.json" ]; then
            cp "$SOURCE_DIR/portfolio_data.json" "$BACKUP_DIR/portfolio_data.json.$(date +%Y%m%d_%H%M%S)"
            echo "  ✅ portfolio_data.json 已备份"
        fi
        echo ""
        
        # 提交并推送
        echo "📤 正在同步到 GitHub..."
        
        # 添加所有更改
        git add -A
        
        # 检查是否有更改
        if git diff --staged --quiet; then
            echo "📝 无新数据需要提交"
        else
            git commit -m "自动备份交易数据 $(date '+%Y-%m-%d %H:%M:%S')"
            echo "✅ 已提交"
            
            gh repo sync
            if [ $? -eq 0 ]; then
                echo "✅ 已同步到 GitHub"
            else
                echo "⚠️ 同步失败"
            fi
        fi
        
        echo ""
        echo "========================================="
        echo "  备份完成 - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================="
        ;;
        
    *)
        # ============================================
        # 默认模式：同步报告
        # ============================================
        echo "========================================="
        echo "     同步报告 - $(date '+%Y-%m-%d %H:%M:%S')"
        echo "========================================="
        echo ""
        
        # 检查 Git 状态
        echo "📊 Git 状态:"
        git status --short
        echo ""
        
        # 检查最近提交
        echo "📝 最近提交:"
        git log --oneline -5
        echo ""
        
        # 检查远程分支
        echo "🌿 远程分支:"
        git branch -r
        echo ""
        
        # 检查未推送的提交
        echo "📤 未推送的提交:"
        git log origin/main..HEAD --oneline 2>/dev/null || echo "无"
        echo ""
        
        # 检查股票服务状态
        echo "📈 股票监测系统状态:"
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5006 2>/dev/null | grep -q "200"; then
            echo "  ✅ 运行中 (端口 5006)"
        else
            echo "  ❌ 未运行"
        fi
        echo ""
        
        echo "========================================="
        echo "     报告生成完成"
        echo "========================================="
        ;;
esac
