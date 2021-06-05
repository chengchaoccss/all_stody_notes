# all_stody_notes
记录日常学习笔记

2.生成SSH KEY
$ ssh-keygen -t rsa -C 44600937@qq.com

注意：这里的邮箱填写你提交代码时要用的邮箱

3.查看.pub文件
$ cd ~/.ssh 切换目录到这个路径

$ vim id_rsa.pub 将这个文件的内容显示到终端上

当然你也可以直接前往.shh文件所在的路径（前往~/.ssh 这个路径），然后用xcode打开.pub这个文件，同样可以看到里面的内容

4.将KEY添加到github或gitlab等
