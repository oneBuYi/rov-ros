# Git 常用命令速查

## 切换到 feature 分支

```bash
# 新的一天，先切到自己的开发分支
git checkout feature/gcs
git checkout feature/grid
git checkout feature/video
git checkout develop
```

## 同步 develop 到当前分支

```bash
# 拉取远端最新信息
git fetch --all

# 查看 develop 有没有新提交（HEAD 即当前分支）
git log HEAD..origin/develop

# 如果有更新，合并到当前分支
git merge origin/develop
```

## 修改与提交

```bash
# 暂存指定文件
git add docs/ros-guide.md

# 暂存所有修改
git add .

# 提交
git commit -m "feat: description"

# 跳过暂存直接提交已跟踪文件
git commit -am "fix: description"
```

## 推送

```bash
# 推送当前分支到远端
git push origin HEAD

# 首次推送并关联远端
git push -u origin HEAD

# 强制推送（谨慎，仅在自己的分支上使用）
git push --force-with-lease origin HEAD
```

## 创建新分支

```bash
# 基于当前分支快速创建并切换
git checkout -b feature/yyy
```

### 从 develop 开出新分支（远端没有）

基于最新的 develop 新建一个远端不存在的分支，完整流程：

```bash
# 1. 切到 develop 并拉取最新
git checkout develop
git pull

# 2. 创建新分支并切换
git checkout -b feature/zzz

# 3. 首次推送并关联远端
git push -u origin feature/zzz

# 之后正常开发推送即可
git commit -am "feat: xxx"
git push
```

```bash
# 查看本地与远端分支
git branch -a
```

## 合并到 develop

```bash
# 切到 develop
git checkout develop

# 拉取最新
git pull

# 合并 feature 分支
git merge feature/gcs

# 推送
git push origin develop

# 切回 feature 继续开发（- 即上一个分支）
git checkout -
```

## 储藏

```bash
# 暂存当前未提交的修改
git stash

# 查看储藏列表
git stash list

# 恢复最近一次储藏并删除
git stash pop
```

## 撤销与回退

```bash
# 撤销工作区修改（未 add）
git restore <file>

# 取消暂存（已 add 未 commit）
git restore --staged <file>

# 回退最近一次 commit（保留修改在工作区）
git reset --soft HEAD~1

# 回退最近一次 commit（丢弃修改）
git reset --hard HEAD~1

# 查看操作历史（找回误删的 commit）
git reflog
```

## 清理分支

```bash
# 删除已合并的本地分支
git branch -d feature/gcs

# 强制删除本地分支
git branch -D feature/gcs

# 删除远端分支
git push origin --delete feature/gcs
```
