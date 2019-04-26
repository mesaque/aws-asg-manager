import boto3,sys,time,base64

PROJECT_NAME   = '[your-key-name]'
lconfiguration = boto3.client('autoscaling',region_name = 'us-east-1')
ec2            = boto3.client('ec2')
ec2resource    = boto3.resource('ec2')

def get_instance(tag):
    reservations = ec2.describe_instances(
        Filters=[
           tag
        ]
    ).get(
        'Reservations', []
    )

    return reservations[0]

def get_volume(volume_id):
    volumes = ec2.describe_volumes(VolumeIds=[volume_id])
    return volumes['Volumes'][0]

def create_image(InstanceId, DM_name, DM_size, DM_type, DM_delterm):
    obj_image = ec2.create_image(
        BlockDeviceMappings=[
            {
                'DeviceName': DM_name,
                'Ebs': {
                    'DeleteOnTermination': DM_delterm,
                    'VolumeSize': DM_size,
                    'VolumeType': DM_type
                }
            }
        ],
        Description=PROJECT_NAME+" WP" + " " + str(time.ctime()),
        DryRun=False,
        InstanceId=InstanceId,
        Name=PROJECT_NAME+"WP_" + str(time.time()),
        NoReboot=True
    )
    return obj_image

def set_tags( client, instance_name, instance_product ):
    tag = client.create_tags(
        Tags=[
            {
                'Key': 'Name',
                'Value': instance_name
            },
            {
                'Key': 'product',
                'Value': instance_product
            }
        ]
    )
    return tag

def create_lc(lc_paramns, image_id, lc_name):
    lc_paramns['ImageId'] = image_id
    lc_paramns['LaunchConfigurationName'] = lc_name

    response = lconfiguration.create_launch_configuration(
        LaunchConfigurationName= lc_paramns['LaunchConfigurationName'],
        ImageId=lc_paramns['ImageId'],
        KeyName=lc_paramns['KeyName'],
        SecurityGroups=lc_paramns['SecurityGroups'],
        UserData=base64.b64decode(lc_paramns['UserData']),
        InstanceType=lc_paramns['InstanceType'],
        BlockDeviceMappings=[
            {
                'DeviceName': lc_paramns['BlockDeviceMappings'][0]['DeviceName'],
                'Ebs': {
                    'VolumeSize': lc_paramns['BlockDeviceMappings'][0]['Ebs']['VolumeSize'],
                    'VolumeType': lc_paramns['BlockDeviceMappings'][0]['Ebs']['VolumeType'],
                    'DeleteOnTermination': lc_paramns['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination']
                }
            },
        ],
        InstanceMonitoring={
            'Enabled': False
        },
        EbsOptimized=False,
        AssociatePublicIpAddress=True
    )
    return response

def update_asg(asg_name, lc_name):
    asg = lconfiguration.update_auto_scaling_group(AutoScalingGroupName=asg_name,LaunchConfigurationName=lc_name)
    return asg

def get_lc(lc_name):
        _lcs = lconfiguration.describe_launch_configurations(
            LaunchConfigurationNames=[
                lc_name,
            ]
        )
        return _lcs['LaunchConfigurations'][0]

def lambda_handler(event, context):

    instance = get_instance( {'Name':'tag:instance', 'Values':['admin']} )
    ist_id = instance['Instances'][0]['InstanceId']
    vlm_id = instance['Instances'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeId']
    volume = get_volume(vlm_id)
    
    for tag in instance['Instances'][0]['Tags']:
        if tag['Key'] == 'Name':
            instance_name = tag['Value']
    for tag in instance['Instances'][0]['Tags']:
        if tag['Key'] == 'product':
            instance_product = tag['Value']
            
    image = create_image(ist_id, volume['Attachments'][0]['Device'], volume['Size'], volume['VolumeType'], volume['Attachments'][0]['DeleteOnTermination'])

    time.sleep(10)
    
    image_rsc = ec2resource.Image(image['ImageId'])
    snapshot_rsc = ec2resource.Snapshot(image_rsc.block_device_mappings[0]['Ebs']['SnapshotId'])

    set_tags(image_rsc, instance_name, instance_product)
    set_tags(snapshot_rsc, instance_name, instance_product)

    model_lc = get_lc(PROJECT_NAME+'-LC-MODEL')

    ami_id  = image['ImageId']
    lc_name = PROJECT_NAME+"-LC-" + ami_id
    lc      = create_lc(model_lc, ami_id, lc_name)
    asg     = update_asg(PROJECT_NAME+'-ASG',lc_name)