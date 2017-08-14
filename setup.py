from setuptools import setup, find_packages

setup(
    name='OpenWifiTemplates',
    version="0.1",
    description="Old template system for OpenWifi",
    author="Johannes Wegener",
    install_requires=["OpenWifi"],
    entry_points="""
    [OpenWifi.plugin]
    addPluginRoutes=OpenWifiTemplates:addPluginRoutes
    globalPluginViews=OpenWifiTemplates:globalWebViews
    addJobserverTasks=OpenWifiTemplates:addJobserverTasks
    """,
    packages=find_packages(),
    include_package_data=True,
)
