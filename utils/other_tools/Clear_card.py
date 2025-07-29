"""
需求：根据融合项目定义code清除当前融合所有的项目卡以及任务卡
1.根据项目code查询当前所有融合项目示例
    调用撤销项目接口，清除融合所有项目卡
2.根据大Tcode拿所有进行中的大T
    撤销大T撤销任务卡
"""

import requests
import logging
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectCleaner:
    def __init__(self, api_base_url: str, auth_token: str, workflow_BASE_URL: str, iam_token: str):
        """
        初始化项目清理器

        Args:
            api_base_url: API基础URL
            auth_token: 认证令牌
        """
        self.api_base_url = api_base_url
        self.auth_token = auth_token
        self.workflow_BASE_URL = workflow_BASE_URL
        self.headers = {
            'token': auth_token,
            'Content-Type': 'application/json'
        }
        self.workflow_headers = {
            'token': iam_token
        }

    def get_fusion_projects_by_code(self, project_code: str) -> List[Dict[str, Any]]:
        """
        根据项目code查询当前所有融合项目

        Args:
            project_code: 项目code

        Returns:
            融合项目列表
        """
        url = f"{self.api_base_url}/restful/standard/taskengine-mgr/v1/projects/get-trace-list"
        data = {
                "locale": "zh_CN",
                "pageIndex": 1,
                "pageSize": 500,
                "startTimeFrom": "2025/01/01 10:33:29",
                "startTimeTo": "2025/12/25 10:33:29",
                "projectCode": project_code,
                "state": -1,
                "type": "All"
            }

        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()

            # 从嵌套的response结构中提取data列表
            response_data = response.json().get("response", {})
            projects = response_data.get("data", [])

            # 提取所有项目的serialNumber
            serial_numbers = [project.get("serialNumber") for project in projects if "serialNumber" in project]
            return serial_numbers
        except requests.exceptions.RequestException as e:
            logger.error(f"获取融合项目失败: {e}")
            return []

    def revoke_fusion_project(self, project_id: str) -> bool:
        """
        调用撤销项目接口，清除融合项目卡

        Args:
            project_id: 项目ID

        Returns:
            操作是否成功
        """
        url = f"{self.api_base_url}/restful/standard/taskengine-mgr/v1/projects/abort-project"
        data = {
                "serialNumber": project_id,
                "personInCharge": "wenwu@digiwin.com",
                "locale": "zh_CN",
                "comment": "123"
            }

        try:
            response = requests.post(url, headers=self.headers,json=data)
            response.raise_for_status()
            logger.info(f"成功撤销融合项目: {project_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"撤销融合项目失败: {e}")
            return False

    def get_active_tasks_by_code(self, t_code: str) -> List[Dict[str, Any]]:
        """
        根据大T code获取所有进行中的大T任务

        Args:
            t_code: 大T code

        Returns:
            进行中的大T任务列表
        """
        url = f"{self.workflow_BASE_URL}/restful/standard/workflow/mgr/v1/api/process/inst/list"
        data = {
                "processId": t_code,
                "serialNumber": "",
                "state": None,
                "pageNum": 1,
                "pageSize": 200
            }

        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()

            # 解析嵌套结构：先获取response字段，再获取其内部的data.records
            response_data = response.json().get("response", {})
            task_data = response_data.get("data", {})
            records = task_data.get("records", [])
            # 提取每个记录中的serialNumber
            records = [record for record in records if record['completeState'] == 0]
            serial_numbers = [record.get("serialNumber") for record in records]
            return serial_numbers
        except requests.exceptions.RequestException as e:
            logger.error(f"获取大T任务失败: {e}")
            return []

    def revoke_task(self, task_id: str) -> bool:
        """
        撤销大T任务卡

        Args:
            task_id: 任务ID

        Returns:
            操作是否成功
        """
        url = f"{self.workflow_BASE_URL}/restful/standard/workflow/api/process/abort"
        data = {
                "comment": "这是撤销意见",
                "performerId": "PLMtest001",
                "serialNumber": task_id
            }

        try:
            response = requests.post(url, headers=self.workflow_headers, json=data)
            response.raise_for_status()
            logger.info(f"成功撤销任务: {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"撤销任务失败: {e}")
            return False

    def clean_projects_by_code(self, project_code: str) -> None:
        """
        根据项目code清除所有融合项目卡

        Args:
            project_code: 项目code
        """
        logger.info(f"开始清除项目code为 {project_code} 的融合项目卡")
        fusion_projects = self.get_fusion_projects_by_code(project_code)
        print(f"清除的项目总数{len(fusion_projects)}")

        if not fusion_projects:
            logger.info(f"未找到项目code为 {project_code} 的融合项目")
            return

        for project_id in fusion_projects:
            if project_id:
                self.revoke_fusion_project(project_id)
            else:
                logger.warning("融合项目缺少ID，跳过撤销")

    def clean_tasks_by_code(self, t_code: str) -> None:
        """
        根据大T code清除所有进行中的大T任务卡

        Args:
            t_code: 大T code
        """
        logger.info(f"开始清除大T code为 {t_code} 的任务卡")
        active_tasks = self.get_active_tasks_by_code(t_code)

        if not active_tasks:
            logger.info(f"未找到大T code为 {t_code} 的进行中任务")
            return
        print(f"撤销总数为{len(active_tasks)}")
        for task_id in active_tasks:
            if task_id:
                self.revoke_task(task_id)
            else:
                logger.warning("任务缺少ID，跳过撤销")


def main():
    # 配置信息
    API_BASE_URL = "https://taskengine-test.apps.digiwincloud.com.cn"  #华为测试区
    workflow_BASE_URL = 'https://workflow-test.apps.digiwincloud.com.cn'
    AUTH_TOKEN = "Athena,c041fd2b-7dcd-493c-8407-b04e3dbff58a"  # mgrtoken 需要保证tenant一致
    iam_token = "25692fab-063b-4965-8e1d-a5cc326d0406"

    # 项目和大T的code
    PROJECT_CODE = "PU_b1c68f4210000ba6"  # 替换为实际项目code___要是子项目！！！
    T_CODES = ["PC_6a660e02100013a0"]  # 替换为实际大T code

    # 初始化清理器
    cleaner = ProjectCleaner(API_BASE_URL, AUTH_TOKEN,workflow_BASE_URL,iam_token)

    # 清除融合项目卡
    # cleaner.clean_projects_by_code(PROJECT_CODE)

    # 清除大T任务卡
    for T_CODE in T_CODES:
        cleaner.clean_tasks_by_code(T_CODE)


    logger.info("清理任务完成")


if __name__ == "__main__":
    main()