from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from pkg.platform.types import message as platform_message
from pkg.plugin.events import PersonMessageReceived, GroupMessageReceived, NormalMessageResponded, GroupNormalMessageReceived
from pkg.provider import entities as llm_entities
from plugins.Waifu.cells.generator import Generator
from pkg.platform.types import *
import os
import yaml
from datetime import datetime
import typing
import copy
from pkg.core import app, entities as core_entities

def convert_datetime(obj):
    """
    将 datetime 对象转换为 ISO 格式的字符串
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    
    if isinstance(obj, list):  # 如果是列表，递归转换
        return [convert_datetime(item) for item in obj]
    
    if isinstance(obj, dict):  # 如果是字典，递归转换
        return {key: convert_datetime(value) for key, value in obj.items()}
    
    if isinstance(obj, llm_entities.Message):  # 如果是 Message 对象，检查其中的 datetime 字段
        # 如果 content 是 datetime 对象，转换为字符串
        if isinstance(obj.content, datetime.datetime):
            obj.content = obj.content.isoformat()
        # 处理可能包含 datetime 对象的其他字段，例如 'role'
        if isinstance(obj.role, datetime.datetime):
            obj.role = obj.role.isoformat()
        # 继续检查其他字段（如果有）
        if isinstance(obj.tool_calls, datetime.datetime):
            obj.tool_calls = obj.tool_calls.isoformat()
        if isinstance(obj.tool_call_id, datetime.datetime):
            obj.tool_call_id = obj.tool_call_id.isoformat()
        return obj

    return obj



import datetime

# 注册插件
@register(name="Remember", description="让AI拥有记忆", version="0.1", author="s2cr3t")
class Remember(BasePlugin):

    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.ap = host.ap
        self.memory_dir = "data/plugins/remember"
        os.makedirs(self.memory_dir, exist_ok=True)  # 确保目录存在
        self._generator = Generator(self.ap)
        self.waifu_cache: typing.Dict[str, Remember] = {}

    # 异步初始化
    async def initialize(self):
        need_save_memory = True
        pass

    @llm_func(name="Remember")
    async def Remember(self, query, important: str, size: int = 100) -> str:
        """Call this function to Remember the important things when asking you to remember something.or you thingk that is importantthings.

        Args:
            important: important things context.
            size: Number of results to return, default is 100, maximum is 10000.

        Returns:
            status: return status
        """
        
        # 获取 target_id, target_type 和 sender_id
        target_info = {
            "target_id": str(query.launcher_id),
            "sender_id": str(query.sender_id),
            "target_type": str(query.launcher_type).split(".")[-1].lower(),  # 获取枚举值的小写形式
        }
        self.target_id = target_info["target_id"]
        self.target_type = target_info["target_type"]
        self.sender_id = target_info["sender_id"]
        
        # 获取当前日期和时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构造YAML文件路径，文件名使用sender_id
        yaml_file = os.path.join(self.memory_dir, f"{self.sender_id}_memory.yaml")
        
        # 读取现有的记忆数据
        if os.path.exists(yaml_file):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                memory_data = yaml.safe_load(f) or {}
        else:
            memory_data = {}

        # 将新的记忆信息添加到字典中
        memory_data[timestamp] = {
            "important": important,
            "target_id": target_info["target_id"],
            "target_type": target_info["target_type"],
            "sender_id": target_info["sender_id"],
        }

        # 写回到YAML文件
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(memory_data, f, allow_unicode=True, default_flow_style=False)

        return f"已记住重要信息: {important}"

    @llm_func(name="GetRemember")
    async def GetRemember(self, query) -> str:
        """当有人问你关于他自身的信息时，调用该函数获取你的记忆

        Args:

        Returns:
            这个函数会返回关于指定人员的全部记忆信息，当然也有可能什么也不返回，如果什么都没有返回，或返回的不是当前用户提问的信息相关时，不要告诉他们你在调用函数，只需要说你不记得了就好
        """
        
        # 获取 target_id, target_type 和 sender_id
        target_info = {
            "target_id": str(query.launcher_id),
            "sender_id": str(query.sender_id),
            "target_type": str(query.launcher_type).split(".")[-1].lower(),  # 获取枚举值的小写形式
        }
        self.target_id = target_info["target_id"]
        self.target_type = target_info["target_type"]
        self.sender_id = target_info["sender_id"]
        
        # 构造YAML文件路径，文件名使用sender_id
        yaml_file = os.path.join(self.memory_dir, f"{self.sender_id}_memory.yaml")
        
        # 如果文件存在，读取内容
        if os.path.exists(yaml_file):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                memory_data = yaml.safe_load(f) or {}
            
            # 检查是否有记忆
            if memory_data:
                # 返回记忆内容
                memories = "\n".join([f"{timestamp}: {memory['important']}" for timestamp, memory in memory_data.items()])
                return f"我记得以下信息：\n{memories}"
        
        # 如果没有记忆，返回空内容
        return "我不记得了。"
    '''
    @handler(GroupMessageReceived)
    async def person_message_received(self, ctx: EventContext):
        
        if not await self._access_control_check(ctx):
            return
        print("GroupMessageReceived")
        await self._request_group_reply(ctx)
        '''

    async def _request_group_reply(self, ctx: EventContext):
        launcher_id = ctx.event.launcher_id
        sender = ctx.event.query.message_event.sender.member_name
        msg = await self._vision(ctx)  # 用眼睛看消息？
        await self._group_reply(ctx)

    def _remove_blank_lines(self, text: str) -> str:
        lines = text.split("\n")
        non_blank_lines = [line for line in lines if line.strip() != ""]
        return "\n".join(non_blank_lines)

    async def _reply(self, ctx: EventContext, response: str, event_trigger: bool = False):
        response_fixed = self._remove_blank_lines(response)
        await ctx.event.query.adapter.reply_message(ctx.event.query.message_event, platform_message.MessageChain([f"{response_fixed}"]), False)
        if event_trigger:
            await self._emit_responded_event(ctx, response_fixed)

    async def _emit_responded_event(self, ctx: EventContext, response: str):
        query = ctx.event.query
        session = await self.ap.sess_mgr.get_session(query)
        await self.ap.plugin_mgr.emit_event(
            event=NormalMessageResponded(
                launcher_type=query.launcher_type.value,
                launcher_id=query.launcher_id,
                sender_id=query.sender_id,
                session=session,
                prefix="",
                response_text=response,
                finish_reason="stop",
                funcs_called=[],
                query=query,
            )
        )

    

    async def _send_group_reply(self, ctx: EventContext):
        """
        调用模型生成群聊回复
        """
        query = ctx.event.query
        msg = ctx.event.query.message_chain  # 获取消息链

        # 将消息链中的内容提取为一个字符串
        msg_content = ''.join([str(item) for item in msg])  # 将消息内容拼接成一个字符串

        # 构造消息对象，确保传递的 content 是字符串
        messages = []
        messages.append(llm_entities.Message(role="user", content=msg_content))

        model_info = await self.ap.model_mgr.get_model_by_name(self.ap.provider_cfg.data["model"])
        print(model_info)

        # 调用模型生成回复
        response = await model_info.requester.call(None, model=model_info, messages=messages)
        print("Response:", response)  # 输出 response，查看是否包含 datetime 对象

        # 递归转换 response 中的 datetime 对象
        response = convert_datetime(response)

        # 发送回复
        await self._reply(ctx, f"{response}", True)







    


    async def _group_reply(self, ctx: EventContext):
        launcher_id = ctx.event.launcher_id

        await self._send_group_reply(ctx)

    async def _vision(self, ctx: EventContext) -> str:
        # 参考自preproc.py PreProcessor
        query = ctx.event.query
        has_image = False
        content_list = []

        session = await self.ap.sess_mgr.get_session(query)
        conversation = await self.ap.sess_mgr.get_conversation(session)
        use_model = conversation.use_model

        for me in query.message_chain:
            if isinstance(me, platform_message.Plain):
                content_list.append(llm_entities.ContentElement.from_text(me.text))
            elif isinstance(me, platform_message.Image):
                if self.ap.provider_cfg.data["enable-vision"] and use_model:
                    if me.url is not None:
                        has_image = True
                        content_list.append(llm_entities.ContentElement.from_image_url(str(me.url)))
                    elif me.base64 is not None:
                        has_image = True
                        content_list.append(llm_entities.ContentElement.from_image_base64(str(me.base64)))
        if not has_image:
            return str(query.message_chain)


    async def _access_control_check(self, ctx: EventContext) -> bool:
        """
        访问控制检查，根据配置判断是否允许继续处理
        :param ctx: 包含事件上下文信息的 EventContext 对象
        :return: True if allowed to continue, False otherwise
        """      
        text_message = str(ctx.event.query.message_chain)
        launcher_id = ctx.event.launcher_id
        sender_id = ctx.event.sender_id
        launcher_type = ctx.event.launcher_type
        event_type = "PMR"
        if isinstance(ctx.event, GroupNormalMessageReceived):
            event_type = "GNMR"
        elif isinstance(ctx.event, GroupMessageReceived):
            event_type = "GMR"

        # 黑白名单检查
        mode = self.ap.pipeline_cfg.data["access-control"]["mode"]
        sess_list = set(self.ap.pipeline_cfg.data["access-control"].get(mode, []))

        found = (launcher_type == "group" and "group_*" in sess_list) or (launcher_type == "person" and "person_*" in sess_list) or f"{launcher_type}_{launcher_id}" in sess_list

        if (mode == "whitelist" and not found) or (mode == "blacklist" and found):
            reason = "不在白名单中" if mode == "whitelist" else "在黑名单中"
            self.ap.logger.info(f"拒绝访问: {launcher_type}_{launcher_id} {reason}。")
            return False


        return True

    async def _handle_command(self, ctx: EventContext) -> typing.Tuple[bool, bool]:
            
            return None








    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message  # 这里的 event 即为 GroupNormalMessageReceived 的对象
        if msg == "hello":  # 如果消息为hello

            # 输出调试信息
            self.ap.logger.debug("hello, {}".format(ctx.event.sender_id))

            # 回复消息 "hello, everyone!"
            ctx.add_return("reply", ["hello, everyone!"])

            # 阻止该事件默认行为（向接口获取回复）
            ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass