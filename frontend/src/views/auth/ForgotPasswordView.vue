<template>
  <section class="auth-panel">
    <p class="eyebrow">ACCOUNT RECOVERY</p>
    <h1>找回密码</h1>
    <p class="intro">当前系统默认离线运行，不发送短信或邮件。请根据账号状态选择对应的恢复方式。</p>
    <div class="card" style="margin-top: 22px">
      <div class="status-line"><span class="status-pill success">离线说明</span><span class="mono">AUTH-RECOVERY</span></div>
      <div class="helper-text" style="display: grid; gap: 10px; margin-top: 14px">
        <p>已登录用户进入用户中心修改密码。</p>
        <p>未登录用户联系管理员，由管理员确认身份后重置账号。</p>
      </div>
    </div>
    <div class="auth-links"><RouterLink to="/login">返回登录</RouterLink><RouterLink to="/register">创建账号</RouterLink></div>
  </section>
</template>
