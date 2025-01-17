# -*- encoding: utf-8 -*-
"""
cppcheck 扫描任务
"""

import os
import sys
import psutil

from task.scmmgr import SCMMgr
from util.pathlib import PathMgr
from task.codelintmodel import CodeLintModel
from util.subprocc import SubProcController
from util.envset import EnvSet
from util.exceptions import AnalyzeTaskError
from util.exceptions import ConfigError
from util.pathfilter import FilterPathUtil
from util.logutil import LogPrinter

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class Cppcheck(CodeLintModel):
    def __init__(self, params):
        CodeLintModel.__init__(self, params)
        self.sensitive_word_maps = {"cppcheck": "Tool", "Cppcheck": "Tool"}

    def analyze(self, params):
        """执行cppcheck扫描任务

        :param params: 需包含下面键值：
           'rules'： lint扫描的规则列表
           'incr_scan' : 是否增量扫描

        :return: return a :py:class:`IssueResponse`
        """
        source_dir = params.source_dir
        work_dir = params.work_dir
        rules = params["rules"]
        incr_scan = params["incr_scan"]
        relpos = len(source_dir) + 1
        files_path = os.path.join(work_dir, "paths.txt")
        path_mgr = PathMgr()

        toscans = []
        want_suffix = [".cpp", ".cxx", ".cc", ".c++", ".c", ".tpp", ".txx"]
        if incr_scan:
            diffs = SCMMgr(params).get_scm_diff()
            toscans = [
                os.path.join(source_dir, diff.path).replace(os.sep, "/")
                for diff in diffs
                if diff.path.endswith(tuple(want_suffix)) and diff.state != "del"
            ]
        else:
            toscans = [path.replace(os.sep, "/") for path in PathMgr().get_dir_files(source_dir, tuple(want_suffix))]

        toscans = FilterPathUtil(params).get_include_files(toscans, relpos)

        if not toscans:
            LogPrinter.debug("To-be-scanned files is empty ")
            return []

        with open(files_path, "w", encoding="UTF-8") as f:
            f.write("\n".join(toscans))

        id_severity_map = self._get_id_severity_map()  # 获取当前版本cppcheck的 规则名:严重级别 对应关系
        supported_rules = id_severity_map.keys()  # 获取当前版本cppcheck支持的所有规则名
        # 过滤掉当前版本cppcheck不支持的规则
        filtered_rules = [r for r in rules if r not in supported_rules]
        rules = list(set(rules) - set(filtered_rules))

        # 执行 cppcheck 工具
        scan_result_path = self._run_cppcheck(files_path, rules, id_severity_map)

        if not os.path.exists(scan_result_path):
            LogPrinter.info("result is empty ")
            return []

        # 格式化结果
        return self._format_result(source_dir, scan_result_path, rules, supported_rules)

    def _get_id_severity_map(self):
        """获取cppcheck所有规则和严重级别的对应关系

        :return:
        """
        cmd_args = ["cppcheck", "--errorlist", "--xml-version=2"]
        errorlist_path = "cppcheck_errorlist.xml"
        return_code = SubProcController(
            cmd_args,
            cwd=os.environ["CPPCHECK_HOME"],
            stdout_filepath=errorlist_path,
            stderr_line_callback=self.print_log,
            env=EnvSet().get_origin_env(),
        ).wait()
        if return_code != 0:
            raise ConfigError("当前机器环境可能不支持cppcheck执行，请查阅任务日志，根据实际情况适配。")
        with open(errorlist_path, "r") as rf:
            errorlist = rf.read()

        error_root = ET.fromstring(errorlist).find("errors")
        id_severity_map = {error.get("id"): error.get("severity") for error in error_root}
        return id_severity_map

    def _get_needed_visitors(self, id_severity_map, rule_list):
        """cppcheck不能指定规则扫描，只能指定规则级别，这里通过rules获取所属的规则级别"""
        assert rule_list is not None
        # cppcheck默认就是开启error规则（且无法指定enable=error),所以这里取补集
        return {id_severity_map[rule_name] for rule_name in rule_list} - {"error"}

    def _run_cppcheck(self, files_path, rules, id_severity_map):
        """
        执行cppcheck扫描工具
        :param files_path:
        :param rules:
        :param id_severity_map:
        :return:
        """
        CPPCHECK_HOME = os.environ["CPPCHECK_HOME"]
        path_mgr = PathMgr()
        cmd_args = [
            "cppcheck",
            "--quiet",
            '--template="{file}[CODEDOG]{line}[CODEDOG]{id}[CODEDOG]{severity}[CODEDOG]{message}"',
            "--inconclusive",
        ]
        # LogPrinter.info(f'rules after filtering: {rules}')
        if not rules:
            # cmd_args.append('--enable=all')
            cmd_args.append("--enable=warning,style,information")
            cmd_args.append("-j %s" % str(psutil.cpu_count()))
        else:
            visitors = self._get_needed_visitors(id_severity_map, rules)
            if visitors:
                cmd_args.append("--enable=%s" % ",".join(visitors))
            # rules里出现unusedFunction 才不会开启并行检查
            if "unusedFunction" not in rules:
                cmd_args.append("-j %s" % psutil.cpu_count())

        # 添加自定义正则表达式规则--rule-file
        custom_rules = path_mgr.get_dir_files(os.path.join(CPPCHECK_HOME, "custom_plugins"), ".xml")
        custom_rules = ["--rule-file=" + rule for rule in custom_rules]
        cmd_args.extend(custom_rules)
        # 添加代码补丁配置cfg --library
        custom_cfgs = path_mgr.get_dir_files(os.path.join(CPPCHECK_HOME, "custom_cfg"), ".cfg")
        custom_cfgs = ["--library=" + cfg for cfg in custom_cfgs]
        cmd_args.extend(custom_cfgs)

        # 指定扫描文件
        cmd_args.append("--file-list=%s" % files_path)
        scan_result_path = "cppcheck_result.xml"
        self.print_log(f"cmd: {' '.join(cmd_args)}")
        SubProcController(
            cmd_args,
            cwd=CPPCHECK_HOME,
            stderr_filepath=scan_result_path,
            stderr_line_callback=self._error_callback,
            stdout_line_callback=self.print_log,
        ).wait()
        if not os.path.exists(scan_result_path):
            return scan_result_path
        if sys.platform == "win32":
            result_content = open(scan_result_path, "r", encoding="gbk").read()
            open(scan_result_path, "w", encoding="utf-8").write(result_content)
        with open(scan_result_path, "r", encoding="utf-8") as rf:
            scan_result = rf.read()

        if not scan_result:
            return scan_result_path

        # 2019-8-28 偶现因为系统编码输出到结果文件，导致解析失败的情况
        error_msg = "/bin/sh: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)\n"
        if scan_result.startswith(error_msg):
            scan_result = scan_result[len(error_msg) :]

        # self.print_log("%s's result: \n%s" % (scan_result_path, scan_result))

        return scan_result_path

    def _error_callback(self, line):
        """

        :param line:
        :return:
        """
        if line.find("The command line is too long") != -1:
            raise AnalyzeTaskError("执行命令行过长")
        # self.print_log(line)

    def _format_result(self, source_dir, scan_result_path, rules, supported_rules):
        """格式化工具执行结果"""
        issues = []
        relpos = len(source_dir) + 1
        with open(scan_result_path, "r") as rf:
            lines = rf.readlines()
            for line in lines:
                error = line.split("[CODEDOG]")
                if len(error) != 5:
                    LogPrinter.info("该error信息不全或格式有误: %s" % line)
                    continue
                if "" in error:
                    LogPrinter.info("忽略error: %s" % line)
                    continue
                rule = error[2]
                if rule not in supported_rules:  # 没有指定规则时，过滤不在当前版本cppcheck支持的规则中的结果
                    LogPrinter.debug("rule not in supported_rules: %s" % rule)
                    continue
                if rule in ["missingInclude", "MissingIncludeSystem"]:
                    LogPrinter.info("unsupported rule:%s" % rule)
                    continue
                if rule not in rules:
                    continue
                # 格式为{file}[CODEDOG]{line}[CODEDOG]{id}[CODEDOG]{severity}[CODEDOG]{message}
                issue = {}
                issue["path"] = error[0][relpos:]
                issue["line"] = int(error[1])
                issue["column"] = "1"
                issue["msg"] = error[4]
                issue["rule"] = rule
                issues.append(issue)
        return issues

    def check_tool_usable(self, tool_params):
        """
        这里判断机器是否支持运行cppcheck
        1. 支持的话，便在客户机器上扫描
        2. 不支持的话，就发布任务到公线机器扫描
        :return:
        """
        if SubProcController(["cppcheck", "--version"], stderr_line_callback=self.print_log).wait() != 0:
            return []
        return ["analyze"]


tool = Cppcheck

if __name__ == "__main__":
    pass
