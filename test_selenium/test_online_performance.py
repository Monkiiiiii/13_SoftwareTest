# Online Boutique Performance Testing - Enhanced Selenium Test
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class OnlineBoutiquePerformanceTest():
  def setup_method(self, method):
    self.driver = webdriver.Chrome()
    #self.driver=webdriver.Edge()
    self.vars = {}
    # 性能测试数据存储
    self.performance_data = []
    self.test_start_time = time.time()
    self.test_name = "Online Boutique 电商系统功能测试"
    print(f"\n{self.test_name}")
    print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.test_start_time))}")
    print("-" * 50)
  
  def teardown_method(self, method):
    # 只关闭浏览器，不生成详细报告
    self.driver.quit()
  
  def record_step_time(self, step_description, start_time, end_time=None):
    """记录每个步骤的执行时间"""
    if end_time is None:
      end_time = time.time()
    
    duration = end_time - start_time
    step_data = {
      'step': step_description,
      'start_time': time.strftime('%H:%M:%S', time.localtime(start_time)),
      'duration': round(duration * 1000, 2),  # 转换为毫秒
      'timestamp': start_time,
      'status': 'success' if duration < 1.0 else 'warning' if duration < 3.0 else 'error'
    }
    self.performance_data.append(step_data)
    
    # 实时显示执行结果
    status_text = "[成功]" if step_data['status'] == 'success' else "[警告]" if step_data['status'] == 'warning' else "[错误]"
    print(f"{status_text} {step_description} | 用时: {step_data['duration']}ms")
    return duration
  
  def wait_for_page_load(self, timeout=10):
    """等待页面完全加载"""
    WebDriverWait(self.driver, timeout).until(
      lambda driver: driver.execute_script("return document.readyState") == "complete"
    )
  
  def measure_page_load_time(self, url):
    """测量页面加载时间 - 使用多种方法获取准确数据"""
    print(f"\n开始加载页面: {url}")
    start_time = time.time()
    
    # 使用Navigation Timing API获取更准确的页面加载时间
    self.driver.get(url)
    self.wait_for_page_load()
    
    end_time = time.time()
    
    # 获取浏览器原生的页面加载时间数据
    try:
      navigation_timing = self.driver.execute_script("""
        var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
        var timings = performance.timing || {};
        return {
          navigationStart: timings.navigationStart,
          domContentLoaded: timings.domContentLoadedEventEnd,
          loadComplete: timings.loadEventEnd,
          domInteractive: timings.domInteractive,
          responseStart: timings.responseStart,
          responseEnd: timings.responseEnd,
          connectStart: timings.connectStart,
          connectEnd: timings.connectEnd
        };
      """)
      
      # 计算各个阶段的加载时间
      if navigation_timing['navigationStart'] and navigation_timing['loadComplete']:
        total_load_time = navigation_timing['loadComplete'] - navigation_timing['navigationStart']
        dom_load_time = navigation_timing['domContentLoaded'] - navigation_timing['navigationStart']
        dom_interactive_time = navigation_timing['domInteractive'] - navigation_timing['navigationStart']
        response_time = navigation_timing['responseEnd'] - navigation_timing['responseStart']
        connection_time = navigation_timing['connectEnd'] - navigation_timing['connectStart']
        
        load_data = {
          'step': f'页面加载: {url}',
          'total_load_time': total_load_time,
          'dom_load_time': dom_load_time,
          'dom_interactive_time': dom_interactive_time,
          'response_time': response_time,
          'connection_time': connection_time,
          'selenium_load_time': round((end_time - start_time) * 1000, 2),
          'performance_grade': 'A' if total_load_time < 1000 else 'B' if total_load_time < 2000 else 'C' if total_load_time < 3000 else 'D'
        }
        
        print(f"页面加载性能分析:")
        print(f"   总加载时间: {total_load_time}ms")
        print(f"   DOM加载时间: {dom_load_time}ms") 
        print(f"   DOM交互时间: {dom_interactive_time}ms")
        print(f"   服务器响应时间: {response_time}ms")
        print(f"   连接建立时间: {connection_time}ms")
        print(f"   Selenium测量时间: {load_data['selenium_load_time']}ms")
        print(f"   性能等级: {load_data['performance_grade']}")
        
        self.performance_data.append(load_data)
      else:
        # 如果无法获取Navigation Timing，使用Selenium测量的时间
        self.record_step_time(f'页面加载: {url}', start_time, end_time)
    except Exception as e:
      print(f"警告: 获取页面性能数据时出错: {e}")
      self.record_step_time(f'页面加载: {url}', start_time, end_time)
  
  def click_with_timing(self, selector, by_method=By.CSS_SELECTOR, description="点击操作"):
    """带时间测量的点击操作"""
    start_time = time.time()
    try:
      # 等待元素可点击
      element = WebDriverWait(self.driver, 10).until(
        expected_conditions.element_to_be_clickable((by_method, selector))
      )
      element.click()
      end_time = time.time()
      self.record_step_time(description, start_time, end_time)
      
      # 等待页面响应（避免过快操作）
      time.sleep(0.5)
      
    except Exception as e:
      end_time = time.time()
      error_msg = f"{description} (失败: {str(e)[:50]})"
      self.record_step_time(error_msg, start_time, end_time)
      raise
  
  def measure_element_response_time(self, selector, by_method=By.CSS_SELECTOR, action_name="查找元素"):
    """测量元素响应时间"""
    start_time = time.time()
    try:
      element = self.driver.find_element(by_method, selector)
      end_time = time.time()
      self.record_step_time(f"{action_name} - 元素定位", start_time, end_time)
      return element
    except Exception as e:
      end_time = time.time()
      self.record_step_time(f"{action_name} - 元素定位失败", start_time, end_time)
      raise
  
  def get_current_page_metrics(self):
    """获取当前页面的实时性能指标"""
    try:
      metrics = self.driver.execute_script("""
        return {
          url: window.location.href,
          title: document.title,
          loadTime: window.performance.timing.loadEventEnd - window.performance.timing.navigationStart,
          domElements: document.getElementsByTagName('*').length,
          images: document.images.length,
          scripts: document.scripts.length
        };
      """)
      return metrics
    except:
      return {}
  

  
  def test_online_boutique_performance(self):
    """Online Boutique 电商系统完整功能测试"""
    
    # 测量首页加载时间
    self.measure_page_load_time("http://127.0.0.1:56988/")
    
    # 设置窗口大小
    start_time = time.time()
    self.driver.set_window_size(1306, 792)
    self.record_step_time("设置浏览器窗口大小", start_time)
    
    print(f"\n开始模拟用户购物流程...")
    
    # 第一个产品 - 浏览和添加到购物车
    self.click_with_timing(".col-md-4:nth-child(2) .hot-product-card-img-overlay", 
                          By.CSS_SELECTOR, "点击第1个产品 - 查看商品详情")
    
    self.click_with_timing(".cymbal-button-primary", 
                          By.CSS_SELECTOR, "点击添加到购物车按钮 - 第1个商品")
    
    self.click_with_timing("Continue Shopping", 
                          By.LINK_TEXT, "点击继续购物 - 返回商品列表")
    
    # 第二个产品 - 浏览和添加到购物车
    self.click_with_timing(".col-md-4:nth-child(3) .hot-product-card-img-overlay", 
                          By.CSS_SELECTOR, "点击第2个产品 - 查看商品详情")
    
    self.click_with_timing(".cymbal-button-primary", 
                          By.CSS_SELECTOR, "点击添加到购物车按钮 - 第2个商品")
    
    # 清空购物车
    self.click_with_timing(".cymbal-button-secondary", 
                          By.CSS_SELECTOR, "点击清空购物车按钮 - 清空已选商品")
    
    # 第三个产品 - 继续购物
    self.click_with_timing(".col-md-4:nth-child(4) .hot-product-card-img-overlay", 
                          By.CSS_SELECTOR, "点击第3个产品 - 查看商品详情")
    
    self.click_with_timing(".cymbal-button-primary", 
                          By.CSS_SELECTOR, "点击添加到购物车按钮 - 第3个商品")
    
    # 开始结账流程
    self.click_with_timing(".cymbal-button-primary:nth-child(1)", 
                          By.CSS_SELECTOR, "点击结账按钮 - 开始结账流程")
    
    # 完成购物或继续购物
    self.click_with_timing("Continue Shopping", 
                          By.LINK_TEXT, "点击继续购物 - 完成购物流程")
    
    print(f"购物流程测试完成!")
    
    # 简单的测试总结
    total_test_time = time.time() - self.test_start_time
    print(f"\n测试总耗时: {round(total_test_time, 2)}秒")
    print(f"测试步骤数: {len(self.performance_data)}")
    
    # 计算平均响应时间
    click_times = [data['duration'] for data in self.performance_data if 'duration' in data and '点击' in data['step']]
    if click_times:
      avg_click = round(sum(click_times)/len(click_times), 2)
      print(f"平均交互响应时间: {avg_click}ms")
    
    print("测试完成!")

# 运行示例和工具函数
def run_performance_test():
    """运行功能测试的便捷函数"""
    test = OnlineBoutiquePerformanceTest()
    test.setup_method(None)
    try:
        test.test_online_boutique_performance()
    except Exception as e:
        print(f"测试执行中出现错误: {e}")
    finally:
        test.teardown_method(None)

if __name__ == "__main__":
    print("启动 Online Boutique 功能测试...")
    run_performance_test() 