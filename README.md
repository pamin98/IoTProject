# IoT Project
This is a simulation of a Fog Computing Cluster of the topology depicted below. The cluster consists of a server with increased computing capabilities (Nvidia's Jetson Nano) and several other, resource-constrained client nodes. The clients can either choose to run their code locally or offload its execution to the server node. To facilitate this decision, the server node can provide an estimation of the mean waiting time at each point in time, depending on current workload. Furthermore, we assume that the clients have some prior knowledge of their applications latency and therefore can deduce which policy is the most beneficial. In the event that the execution was offloaded but takes longer than initially expected to complete, the client can choose to abort the offloaded execution and run locally.
![Client-Server Topology](https://github.com/pamin98/IoTProject/assets/57448652/e2d0955c-91d9-471b-8836-54fa6e69749c)

During testing, the following microcomputers were utilized:
- Nvidia Jetson Nano (Server)
- Raspberry Pi 3     (Client)
- Raspberry Pi 4     (Client)
- BeagleBoard-xM     (Client)

# Dependencies
- twisted>=14.0.0
- six>=1.10.0
- gcc (any version)

# Queueing Model
The server receives requests that arrive at random times and independently from one another (Poisson Point Process), while the time required for servicing each request is also random and independent from every other request. Therefore, the system can be modeled as an M/M/1 queue, where the server receives requests with an exponential delay of mean value equal to 1/λ, and exponential execution latency of mean value 1/μ:
![image](https://github.com/pamin98/IoTProject/assets/57448652/09e45469-bcb1-4e9c-b428-00461ab7ea6a)

In equilibrium, the following equations apply:
![image](https://github.com/pamin98/IoTProject/assets/57448652/7dae6cf4-80c1-4d4b-807d-269278ffcba8)

where p_n is the probability of n clients residing in the queue.

From the first equation, we obtain:
![image](https://github.com/pamin98/IoTProject/assets/57448652/48967d13-6a24-4c74-b5af-7e29043047f0)

where ρ = λ/μ.
By substituting n = 1 at the second equation, we obtain:
![image](https://github.com/pamin98/IoTProject/assets/57448652/61c5238f-fc0a-4181-b147-2edf224e6a60)

And eventually, if we continue substituting with 2, 3, .., n:
![image](https://github.com/pamin98/IoTProject/assets/57448652/6b09f722-e0e2-4cc7-9808-5e6181bacf77)

From the third equation though:
![image](https://github.com/pamin98/IoTProject/assets/57448652/ead3d927-df71-4772-949b-bade63ff1681)

And thus, the probability of n clients residing in the queue is:
![image](https://github.com/pamin98/IoTProject/assets/57448652/111d04c4-8f68-4c46-9938-705e35a63178)

We can now compute the mean number of clients in the queue:
![image](https://github.com/pamin98/IoTProject/assets/57448652/ed14e32d-bd90-4af9-a455-21512109fab4)

Using Little's Law, we can deduce the average time a client spends in the queue:
![image](https://github.com/pamin98/IoTProject/assets/57448652/efb4ec43-ed7e-418e-8631-62324f048c7f)
