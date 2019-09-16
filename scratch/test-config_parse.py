import yaml

with open("config.yaml", 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)

# if cfg['debug']:
#     print('Debug')
# else:
#     print('No debug')
    
with open("config2.yaml", 'r') as ymlfile:
    cfg2 = yaml.safe_load(ymlfile)

print(cfg)
cfg.update(cfg2)
print(cfg)
